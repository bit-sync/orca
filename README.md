# Orca

Orca is a lightweight alternative to Docker Compose, focusing on simplicity and efficient container orchestration. It provides seamless service management and load balancing capabilities through an intuitive YAML configuration.

## Features

- **Simple Service Management**: Define and manage multiple Docker services
- **Load Balancing**: Built-in Nginx-based load balancing
- **Service Scaling**: Scale services with automatic load balancer reconfiguration
- **Progress Tracking**: Visual feedback during service operations
- **Health Monitoring**: Passive health checks and automatic failover

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/orca.git
   cd orca
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a basic configuration:
   ```yaml
   # orca.yml
   services:
     web:
       image: nginx:latest
       volumes:
         - ./html:/usr/share/nginx/html

   load_balancers:
     web_lb:
       services:
         - name: web
       port: 8080
   ```

4. Start your services:
   ```bash
   ./orca.py up
   ```

## Documentation

For detailed documentation, visit our [GitHub Pages site](https://yourusername.github.io/orca):

- [Getting Started](https://yourusername.github.io/orca/getting-started)
- [Configuration Guide](https://yourusername.github.io/orca/configuration)
- [Load Balancing](https://yourusername.github.io/orca/load-balancing)
- [Examples](https://yourusername.github.io/orca/examples)

## Documentation Development

The documentation is built using Jekyll and hosted on GitHub Pages. To develop the documentation locally:

1. Install Ruby and Bundler
2. Navigate to the docs directory:
   ```bash
   cd docs
   ```
3. Install dependencies:
   ```bash
   bundle install
   ```
4. Start the local server:
   ```bash
   bundle exec jekyll serve
   ```
5. Visit `http://localhost:4000`

The documentation will be automatically built and deployed to GitHub Pages when you push to the main branch.

### Publishing to GitHub Pages

1. Fork this repository
2. Go to your fork's Settings > Pages
3. Under "Source", select "GitHub Actions"
4. Push your changes to the main branch
5. GitHub Actions will automatically build and deploy the documentation
6. Your documentation will be available at `https://yourusername.github.io/orca`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details