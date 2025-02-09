import os
from pathlib import Path
from typing import Dict, List, Any
import docker
import time
import click

class LoadBalancerManager:
    NGINX_TEMPLATE = """
events {{
    worker_connections 1024;
}}

http {{
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;

    upstream {upstream_name} {{
        {algorithm}
        {servers}
    }}

    server {{
        listen 80 default_server;
        server_name _;
        root /usr/share/nginx/html;
        index index.html;

        location / {{
            proxy_pass http://{upstream_name};
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";

            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
            proxy_next_upstream_tries 3;
            proxy_next_upstream_timeout 10s;
            proxy_connect_timeout 5s;
            proxy_send_timeout 10s;
            proxy_read_timeout 10s;
        }}

        location /health {{
            access_log off;
            return 200 'OK';
            add_header Content-Type text/plain;
        }}

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {{
            root   /usr/share/nginx/html;
        }}
    }}
}}
"""

    def __init__(self, client: docker.DockerClient):
        self.client = client
        self.config_dir = Path("/tmp/orca/nginx")
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _create_nginx_config(self, name: str, config: Dict[str, Any], services: Dict[str, Any]) -> str:
        """Create Nginx configuration for a load balancer"""
        service_name = config['services'][0]['name']  # Currently supporting one service per LB
        service_config = services[service_name]
        
        # Calculate the number of backend servers based on service scale
        scale = service_config.get('scale', 1)
        
        # Generate upstream server list
        servers = []
        for i in range(scale):
            instance_name = f"{service_name}_{i + 1}" if scale > 1 else service_name
            weight = config['services'][0].get('weight', 1)
            # Use Docker's internal DNS resolution
            servers.append(f"        server {instance_name}:80 weight={weight};")  

        # Set load balancing algorithm
        algorithm_map = {
            'round_robin': '',  # Default nginx behavior
            'least_conn': 'least_conn;',
            'ip_hash': 'ip_hash;'
        }
        algorithm = algorithm_map.get(config.get('algorithm', 'round_robin'), '')

        # Parse health check config
        health_check = config.get('health_check', {})
        health_check_path = health_check.get('path', '/')
        health_check_interval = health_check.get('interval', '5s')
        health_check_retries = health_check.get('retries', 3)

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Generate the configuration
        nginx_config = self.NGINX_TEMPLATE.format(
            upstream_name=name,
            algorithm=algorithm,
            servers='\n'.join(servers),
            port=config['port']
        )

        # Write configuration to file
        config_file = self.config_dir / f"{name}.conf"
        with open(config_file, 'w') as f:
            f.write(nginx_config)

        return str(config_file)

    def create_load_balancer(self, name: str, config: Dict[str, Any], services: Dict[str, Any]) -> None:
        """Create and start a load balancer container"""
        click.echo(f"Creating load balancer: {name}")

        # Create Nginx configuration
        config_file = self._create_nginx_config(name, config, services)

        try:
            # Create a custom network if it doesn't exist
            network_name = 'orca_network'
            try:
                network = self.client.networks.get(network_name)
            except docker.errors.NotFound:
                network = self.client.networks.create(
                    network_name,
                    driver='bridge',
                    attachable=True
                )

            # Connect all service containers to the network
            service_name = config['services'][0]['name']
            service_config = services[service_name]
            scale = service_config.get('scale', 1)
            
            for i in range(scale):
                instance_name = f"{service_name}_{i + 1}" if scale > 1 else service_name
                try:
                    container = self.client.containers.get(instance_name)
                    try:
                        network.connect(container)
                    except docker.errors.APIError as e:
                        if 'already exists' not in str(e):
                            raise
                except docker.errors.NotFound:
                    click.echo(f"Warning: Service container {instance_name} not found")

            # Create and start the load balancer container
            container = self.client.containers.run(
                image='nginx:latest',
                name=name,
                detach=True,
                ports={f"80/tcp": config['port']},  # Map container port 80 to specified host port
                volumes={
                    config_file: {
                        'bind': '/etc/nginx/nginx.conf',
                        'mode': 'ro'
                    }
                },
                network=network_name  # Connect to the custom network
            )

            click.echo(f"Successfully started load balancer {name} ({container.short_id})")
        except docker.errors.APIError as e:
            click.echo(f"Error starting load balancer {name}: {str(e)}", err=True)

    def remove_load_balancer(self, name: str) -> None:
        """Stop and remove a load balancer container"""
        try:
            container = self.client.containers.get(name)
            container.stop()
            container.remove()
            
            # Clean up configuration file
            config_file = self.config_dir / f"{name}.conf"
            if config_file.exists():
                config_file.unlink()
                
            click.echo(f"Successfully stopped and removed load balancer {name}")
        except docker.errors.NotFound:
            click.echo(f"Load balancer {name} not found")
        except docker.errors.APIError as e:
            click.echo(f"Error stopping load balancer {name}: {str(e)}", err=True)
