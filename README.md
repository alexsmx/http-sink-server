# HTTP Sink Server

A configurable HTTP server that simulates API endpoints and webhook sequences based on YAML configurations. Perfect for testing webhook integrations, API callbacks, and simulating complex API behaviors in development environments.

## Features

- 🔄 Configurable endpoint behaviors via YAML
- 🕒 Supports delayed webhook sequences
- 🎯 Template-based response customization
- 📝 Detailed request logging
- 🧵 Multi-threaded request handling
- 🔌 Configurable callback servers
- 🎲 Random delays and response variations

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/http-sink-server.git
cd http-sink-server
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```
## Usage

1. Configure your endpoints in `endpoints.yaml`:

```yaml
yaml:README.md
config:
default_callback_server: "http://localhost:8000"
endpoints:
/your-endpoint:
description: "Your endpoint description"
method: POST
# ... rest of configuration
```

2. Run the server:
```bash
python http_sink.py --port 4000
```

Optional: Specify a callback URL:

```bash
python http_sink.py --port 4000 --callback-url "http://your-callback-server.com"
```


## Configuration

The server uses a YAML configuration file (`endpoints.yaml`) to define endpoint behaviors. See the example configuration for detailed structure and options.


## Todo Before Open Source Launch

- [ ] Add proper error handling and logging
- [ ] Write comprehensive documentation
  - [ ] Configuration file format
  - [ ] Template variables reference
  - [ ] Webhook sequence configuration
  - [ ] Best practices
- [ ] Add unit tests
- [ ] Add integration tests
- [ ] Create example configurations
- [ ] Add CI/CD pipeline
- [ ] Security review
  - [ ] Input validation
  - [ ] Rate limiting
  - [ ] Security headers
- [ ] Add contribution guidelines
- [ ] Create issue templates
- [ ] Add changelog
- [ ] Add code of conduct
- [ ] Add proper versioning
- [ ] Docker support
- [ ] Environment variables support
- [ ] Add monitoring/metrics
- [ ] Performance optimization
- [ ] Add proper CLI interface
- [ ] Add configuration validation
- [ ] Add SSL/TLS support
- [ ] Add tests

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
