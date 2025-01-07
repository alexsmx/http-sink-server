from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime
import urllib.parse
import argparse
import yaml
import re
import random
import threading
import time
import requests
from typing import Dict, Any
import uuid

class EndpointConfig:
    def __init__(self, config_file: str):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
            # Ensure there's at least an empty config section
            if 'config' not in self.config:
                self.config['config'] = {}
    
    def get_endpoint_config(self, path: str, method: str) -> Dict[str, Any]:
        endpoints = self.config.get('endpoints', {})
        for endpoint, config in endpoints.items():
            if path == endpoint and method == config.get('method', 'GET'):
                # Add endpoint config to the returned config
                config['endpoint'] = {
                    'callback_server': config.get('callback_server', '')
                }
                return config
        return None

    def evaluate_template(self, template: str, context: Dict[str, Any]) -> str:
        """Evaluate template strings with {{expression}}"""
        def replace(match):
            expr = match.group(1).strip()
            if expr.startswith('random_int'):
                min_val, max_val = map(int, re.findall(r'\d+', expr))
                return str(random.randint(min_val, max_val))
            elif expr == 'uuid':
                return str(uuid.uuid4())
            elif expr == 'uuid_hex':
                return uuid.uuid4().hex
            elif expr.startswith('random_choice'):
                # Extract choices from the expression
                choices_str = expr[expr.find('(')+1:expr.find(')')]
                choices = [choice.strip().strip("'\"") for choice in choices_str.split(',')]
                return random.choice(choices)
            
            # Handle fallback syntax with |
            if '|' in expr:
                primary, fallback = expr.split('|')
                primary_value = self._get_nested_value(primary.strip(), context)
                if primary_value:
                    return str(primary_value)
                return str(self._get_nested_value(fallback.strip(), context))
            
            return str(self._get_nested_value(expr, context))

        return re.sub(r'\{\{(.*?)\}\}', replace, template)

    def _get_nested_value(self, expr, context):
        # Handle fallback syntax with |
        if '|' in expr:
            primary, fallback = expr.split('|', 1)
            try:
                primary_value = self._get_nested_value(primary.strip(), context)
                if primary_value is not None:
                    return primary_value
            except (KeyError, AttributeError):
                pass
            return self._get_nested_value(fallback.strip(), context)
        
        # Handle nested keys with dot notation
        parts = expr.split('.')
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, None)
            if value is None:
                break
        return value

    def process_data(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively process all strings in a dictionary/list structure"""
        # Add global config to context
        context['config'] = self.config.get('config', {})
        
        if isinstance(data, str):
            return self.evaluate_template(data, context)
        elif isinstance(data, dict):
            return {k: self.process_data(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.process_data(item, context) for item in data]
        return data

class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.config = EndpointConfig('endpoints.yaml')
        super().__init__(*args, **kwargs)

    def _handle_request(self):
        # Get request details
        timestamp = datetime.now().isoformat()
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''
        query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        
        # Get origin information
        client_host = self.client_address[0]
        client_port = self.client_address[1]
        forwarded_for = self.headers.get('X-Forwarded-For', '')
        real_ip = self.headers.get('X-Real-IP', '')
        host = self.headers.get('Host', '')
        
        # Log request details
        print("\n=== New Request ===")
        print(f"Timestamp: {timestamp}")
        print(f"Method: {self.command}")
        print(f"Path: {self.path}")
        print("\nOrigin Information:")
        print(f"Client Address: {client_host}:{client_port}")
        print(f"X-Forwarded-For: {forwarded_for}")
        print(f"X-Real-IP: {real_ip}")
        print(f"Host: {host}")
        print("\nRequest Details:")
        print(f"Headers: {dict(self.headers)}")
        print(f"Query Params: {query_params}")
        print(f"Body: {body}")
        print("================\n")

        # Check if there's a configured behavior for this endpoint
        endpoint_config = self.config.get_endpoint_config(self.path, self.command)
        
        if endpoint_config:
            request_id = str(uuid.uuid4())[:8]
            print(f"\n[{request_id}] 🎯 Found matching rule for {self.command} {self.path}")
            print(f"[{request_id}] Description: {endpoint_config.get('description', 'No description provided')}")
            
            # Create context for template evaluation
            context = {
                'request': {
                    'base_url': f"http://{self.headers.get('Host', 'localhost')}",
                    'body': json.loads(body) if body else {},
                    'headers': dict(self.headers),
                    'query_params': query_params,
                    'origin': {
                        'ip': self.client_address[0],
                        'port': self.client_address[1],
                        'forwarded_for': self.headers.get('X-Forwarded-For', ''),
                        'real_ip': self.headers.get('X-Real-IP', ''),
                        'host': self.headers.get('Host', '')
                    }
                }
            }

            # Process initial response
            initial_response = endpoint_config.get('initial_response', {})
            processed_response = self.config.process_data(initial_response.get('body', {}), context)
            
            # Send initial response
            self.send_response(initial_response.get('status', 200))
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(processed_response).encode())

            # Update context with initial response
            context['initial_response'] = {'body': processed_response}

            # Handle sequence in a separate thread
            if 'sequence' in endpoint_config:
                sequence_len = len(endpoint_config['sequence'])
                print(f"[{request_id}] 🔄 Scheduling sequence of {sequence_len} actions")
                thread = threading.Thread(
                    target=self._handle_sequence,
                    args=(endpoint_config['sequence'], context, request_id)
                )
                thread.daemon = True
                thread.start()
                print(f"[{request_id}] ✨ Sequence scheduled in background thread")
        else:
            print(f"\n❌ No rules found for {self.command} {self.path}")
            # Default response for unconfigured endpoints
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "message": "Request received (no special rules applied)"}
            self.wfile.write(json.dumps(response).encode())

    def _handle_sequence(self, sequence, context, request_id):
        print(f"\n[{request_id}] Starting sequence execution")
        for i, step in enumerate(sequence, 1):
            print(f"\n[{request_id}] Executing step {i} of {len(sequence)}")
            
            # Handle delay
            if 'delay' in step:
                if isinstance(step['delay'], dict) and 'min' in step['delay'] and 'max' in step['delay']:
                    delay_time = random.uniform(step['delay']['min'], step['delay']['max'])
                    print(f"[{request_id}] Waiting for random delay between {step['delay']['min']}-{step['delay']['max']} seconds: {delay_time:.2f}s")
                else:
                    delay_time = step['delay']
                    print(f"[{request_id}] Waiting for fixed delay: {delay_time}s")
                time.sleep(delay_time)
                print(f"[{request_id}] Delay completed")
            
            # Handle webhook
            if 'webhook' in step:
                webhook = self.config.process_data(step['webhook'], context)
                try:
                    print(f"[{request_id}] Sending webhook to {webhook['url']}")
                    response = requests.request(
                        method=webhook['method'],
                        url=webhook['url'],
                        headers=webhook.get('headers', {}),
                        json=webhook.get('body', {})
                    )
                    print(f"[{request_id}] Webhook response status: {response.status_code}")
                    print(f"[{request_id}] Webhook request body:")
                    print(json.dumps(webhook.get('body', {}), indent=2))
                    print(f"[{request_id}] Webhook response body:")
                    print(json.dumps(response.json() if response.text else {}, indent=2))
                except Exception as e:
                    print(f"[{request_id}] Webhook error: {e}")
        
        print(f"\n[{request_id}] Sequence execution completed")

    def do_GET(self):
        self._handle_request()

    def do_POST(self):
        self._handle_request()

    def do_PUT(self):
        self._handle_request()

    def do_DELETE(self):
        self._handle_request()

def run_server(port=8000):
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, RequestHandler)
    print(f"Starting HTTP sink server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='HTTP Sink Server')
    parser.add_argument('-p', '--port', type=int, default=4000,
                      help='Port to run the server on (default: 4000)')
    parser.add_argument('-c', '--callback-url', type=str,
                      help='Callback server URL (overrides YAML config)')
    
    args = parser.parse_args()
    
    # If callback URL provided, update the config
    if args.callback_url:
        with open('endpoints.yaml', 'r') as f:
            config = yaml.safe_load(f)
            if 'config' not in config:
                config['config'] = {}
            config['config']['callback_server'] = args.callback_url
            yaml.dump(config, f)
    
    run_server(args.port) 