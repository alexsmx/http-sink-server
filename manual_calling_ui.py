import yaml
from flask import Blueprint, render_template_string, request, jsonify, redirect, url_for
import requests
from pathlib import Path
import json

# Create the Blueprint first
manual_calling_bp = Blueprint('manual_calling', __name__)

# HTML templates using Bootstrap for styling
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Manual Calling Interface</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-5">
        <h1>Manual Calling Endpoints</h1>
        <div class="list-group mt-4">
            {% for path, endpoint in endpoints.items() %}
                <!-- Debug info -->
                <div class="mb-3">
                    <p>Debug - Path: {{ path }}</p>
                    <p>Debug - Stripped Path: {{ path.lstrip('/') }}</p>
                    <a href="/manual_calling/{{ path.lstrip('/') }}" 
                       class="list-group-item list-group-item-action">
                        <h5 class="mb-1">{{ path }}</h5>
                        <p class="mb-1">{{ endpoint.description }}</p>
                    </a>
                </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

FORM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ endpoint_config.form.title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
</head>
<body>
    <div class="container mt-5">
        <!-- Debug info -->
        <div class="alert alert-info">
            <p>Debug - Endpoint Name: {{ endpoint_name }}</p>
            <p>Debug - Form Title: {{ endpoint_config.form.title }}</p>
        </div>

        <a href="/manual_calling" class="btn btn-secondary mb-3">← Back to Endpoints</a>
        <h1>{{ endpoint_config.form.title }}</h1>
        <p>{{ endpoint_config.description }}</p>
        
        <form id="endpointForm" class="mt-4">
            {% for field in endpoint_config.form.fields %}
                <div class="mb-3">
                    <label for="{{ field.name }}" class="form-label">{{ field.label }}</label>
                    
                    {% if field.type == 'select' %}
                        <select name="{{ field.name }}" id="{{ field.name }}" 
                                class="form-select" {% if field.required %}required{% endif %}>
                            {% for option in field.options %}
                                <option value="{{ option.value }}" 
                                        {% if option.value == field.default %}selected{% endif %}>
                                    {{ option.label }}
                                </option>
                            {% endfor %}
                        </select>
                    
                    {% elif field.type == 'textarea' %}
                        <textarea name="{{ field.name }}" id="{{ field.name }}" 
                                 class="form-control" {% if field.required %}required{% endif %}
                                 rows="3">{{ field.default }}</textarea>
                    
                    {% else %}
                        <input type="{{ field.type }}" 
                               name="{{ field.name }}" 
                               id="{{ field.name }}"
                               class="form-control"
                               value="{{ field.default }}"
                               {% if field.required %}required{% endif %}
                               {% if field.pattern %}pattern="{{ field.pattern }}"{% endif %}>
                    {% endif %}
                </div>
            {% endfor %}
            
            <button type="submit" class="btn btn-primary">Submit</button>
        </form>

        <div id="response" class="mt-4" style="display: none;">
            <h3>Response:</h3>
            <pre id="responseContent" class="bg-light p-3 rounded"></pre>
        </div>
    </div>

    <script>
        $(document).ready(function() {
            $('#endpointForm').on('submit', function(e) {
                e.preventDefault();
                
                var formData = {};
                $(this).serializeArray().forEach(function(item) {
                    formData[item.name] = item.value;
                });

                $.ajax({
                    url: 'http://localhost:4000/{{ endpoint_name }}',
                    type: 'POST',
                    data: JSON.stringify(formData),
                    contentType: 'application/json',
                    success: function(response) {
                        $('#responseContent').text(JSON.stringify(response, null, 2));
                        $('#response').show();
                    },
                    error: function(xhr) {
                        $('#responseContent').text(JSON.stringify(xhr.responseJSON || xhr.responseText, null, 2));
                        $('#response').show();
                    }
                });
            });
        });
    </script>
</body>
</html>
"""

def extract_endpoint_info(config):
    """Extract only the necessary information for the UI from the endpoints config"""
    ui_endpoints = {}
    
    for path, endpoint_config in config.get('endpoints', {}).items():
        if endpoint_config.get('type') == 'manual_calling':
            ui_endpoints[path] = {
                'description': endpoint_config.get('description', ''),
                'form': {
                    'title': endpoint_config.get('form', {}).get('title', 'Form'),
                    'fields': endpoint_config.get('form', {}).get('fields', [])
                }
            }
    
    print("Simplified UI endpoints:", json.dumps(ui_endpoints, indent=2))
    return ui_endpoints

def load_endpoints_config():
    config_path = Path("endpoints.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)
        return extract_endpoint_info(config)

def get_sink_server_url():
    """Get the URL of the sink server from the running configuration"""
    return f"http://localhost:4000"  # Default sink server port

# Routes defined after Blueprint creation
@manual_calling_bp.route('/manual_calling')
def index():
    endpoints = load_endpoints_config()
    return render_template_string(
        INDEX_TEMPLATE,
        endpoints=endpoints
    )

@manual_calling_bp.route('/manual_calling/<endpoint_name>')
def show_form(endpoint_name):
    endpoints = load_endpoints_config()
    endpoint_config = endpoints.get(f'/{endpoint_name}')
    
    if not endpoint_config:
        return "Endpoint not found", 404
    
    return render_template_string(
        FORM_TEMPLATE,
        endpoint_config=endpoint_config,
        endpoint_name=endpoint_name
    )

# @manual_calling_bp.route('/manual_calling/<endpoint>/submit', methods=['POST'])
# def submit_form(endpoint):
#     config = load_endpoints_config()
#     endpoint_config = config['endpoints'].get(f'/{endpoint}')
    
#     if not endpoint_config:
#         return jsonify({"error": "Endpoint not found"}), 404

#     # Use the sink server URL instead of the UI server URL
#     sink_url = f"{get_sink_server_url()}/{endpoint}"
    
#     try:
#         # Make the request to the sink server
#         response = requests.post(
#             sink_url,
#             json=request.form.to_dict(),
#             headers={'Content-Type': 'application/json'}
#         )
        
#         return jsonify({
#             "message": "Request submitted successfully",
#             "status_code": response.status_code,
#             "response": response.json() if response.headers.get('content-type') == 'application/json' else response.text
#         })
    
#     except requests.RequestException as e:
#         return jsonify({
#             "error": "Failed to submit request",
#             "details": str(e)
#         }), 500 