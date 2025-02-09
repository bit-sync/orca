import click
import docker
import yaml
import time
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm

from .load_balancer import LoadBalancerManager

class DockerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.config = {}
        self.services = {}
        self.load_balancers = {}
        self.lb_manager = LoadBalancerManager(self.client)

    def load_config(self, config_file: str) -> None:
        """Load configuration from orca.yml file"""
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
            self.services = self.config.get('services', {})
            self.load_balancers = self.config.get('load_balancers', {})

    def up(self, service_name: str = None, rebuild: bool = False) -> None:
        """Start services defined in the configuration with scaling support
        
        Args:
            service_name: Optional name of specific service to start
            rebuild: If True, force rebuild/pull of images before starting
        """
        services_to_start = {service_name: self.services[service_name]} if service_name else self.services

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

        # First start all services
        total_instances = sum(config.get('scale', 1) for config in services_to_start.values())
        with tqdm(total=total_instances, desc="Starting services", unit="container") as pbar:
            for name, config in services_to_start.items():
                scale = config.get('scale', 1)
                pbar.set_postfix_str(f"Current service: {name}")
                
                # Extract container configuration
                image = config.get('image')
                expose_ports = config.get('expose', [])
                environment = config.get('environment', {})
                volumes = config.get('volumes', [])

                # Set up port exposures (no host binding)
                port_bindings = {}
                for port in expose_ports:
                    # Format: {container_port/protocol: None} for internal exposure only
                    port_bindings[f"{port}/tcp"] = None

                # Convert volumes to docker format
                volume_bindings = {}
                for volume in volumes:
                    host_path, container_path = volume.split(':')
                    volume_bindings[str(Path(host_path).absolute())] = {
                        'bind': container_path,
                        'mode': 'rw'
                    }

                # Start containers based on scale
                for instance in range(scale):
                    instance_name = f"{name}_{instance + 1}" if scale > 1 else name

                    try:
                        # Pull/rebuild image if requested
                        if rebuild:
                            click.echo(f"Pulling latest image for {name}: {image}")
                            self.client.images.pull(image)

                        container = self.client.containers.run(
                            image=image,
                            name=instance_name,
                            detach=True,
                            ports=port_bindings,  # Only expose ports internally
                            environment=environment,
                            volumes=volume_bindings,
                            network=network_name  # Connect to the custom network
                        )
                        pbar.update(1)
                        pbar.set_postfix_str(f"Started {instance_name} ({container.short_id})")
                    except docker.errors.APIError as e:
                        click.echo(f"Error starting {instance_name}: {str(e)}", err=True)
        
        # Wait for services to be ready before starting load balancers
        if not service_name and self.load_balancers:
            with tqdm(total=len(self.load_balancers), desc="Starting load balancers", unit="lb") as pbar:
                for lb_name, lb_config in self.load_balancers.items():
                    pbar.set_postfix_str(f"Waiting for services...")
                    
                    # Wait for required services to be ready
                    for service_config in lb_config.get('services', []):
                        service_name = service_config['name']
                        service_scale = self.services[service_name].get('scale', 1)
                        
                        # Wait for each instance to be ready
                        for i in range(service_scale):
                            instance_name = f"{service_name}_{i + 1}" if service_scale > 1 else service_name
                            max_retries = 10
                            retry_count = 0
                            
                            while retry_count < max_retries:
                                try:
                                    container = self.client.containers.get(instance_name)
                                    if container.status == 'running':
                                        break
                                except:
                                    pass
                                retry_count += 1
                                time.sleep(1)
                    
                    pbar.set_postfix_str(f"Starting {lb_name}")
                    self.lb_manager.create_load_balancer(lb_name, lb_config, self.services)
                    pbar.update(1)

    def down(self, service_name: str = None) -> None:
        """Stop and remove containers including scaled instances and load balancers"""
        # First stop load balancers if we're stopping all services
        if not service_name and self.load_balancers:
            with tqdm(total=len(self.load_balancers), desc="Stopping load balancers", unit="lb") as pbar:
                for lb_name in self.load_balancers:
                    pbar.set_postfix_str(f"Stopping {lb_name}")
                    self.lb_manager.remove_load_balancer(lb_name)
                    pbar.update(1)

        # Then stop services
        services_to_stop = [service_name] if service_name else self.services.keys()
        total_instances = sum(self.services[name].get('scale', 1) if name in self.services else 1
                             for name in services_to_stop)
        
        with tqdm(total=total_instances, desc="Stopping services", unit="container") as pbar:
            for name in services_to_stop:
                scale = self.services[name].get('scale', 1) if name in self.services else 1
                pbar.set_postfix_str(f"Current service: {name}")
            
            # Stop all instances of the service
            for instance in range(scale):
                instance_name = f"{name}_{instance + 1}" if scale > 1 else name
                try:
                    container = self.client.containers.get(instance_name)
                    container.stop()
                    container.remove()
                    pbar.update(1)
                    pbar.set_postfix_str(f"Stopped {instance_name}")
                except docker.errors.NotFound:
                    click.echo(f"Container {instance_name} not found")
                except docker.errors.APIError as e:
                    click.echo(f"Error stopping {instance_name}: {str(e)}", err=True)

    def ps(self) -> None:
        """List running containers with scale information and load balancers"""
        containers = self.client.containers.list()
        if not containers:
            click.echo("No running containers")
            return

        # Group containers by service name
        service_containers = {}
        lb_containers = []
        for container in containers:
            if container.name in self.load_balancers:
                lb_containers.append(container)
            else:
                service_name = container.name.rsplit('_', 1)[0] if '_' in container.name else container.name
                if service_name not in service_containers:
                    service_containers[service_name] = []
                service_containers[service_name].append(container)

        # Print services
        if service_containers:
            click.echo("\nSERVICES:")
            click.echo("SERVICE\t\tSCALE\tCONTAINER ID\tNAME\t\tSTATUS\t\tPORTS")
            for service_name, containers in service_containers.items():
                scale = len(containers)
                for container in containers:
                    # Handle port mapping format from Docker API
                    port_mappings = container.attrs['NetworkSettings']['Ports']
                    port_list = []
                    if port_mappings:
                        for container_port, host_bindings in port_mappings.items():
                            if host_bindings:  # Check if port is actually mapped
                                for binding in host_bindings:
                                    host_port = binding['HostPort']
                                    # Remove the protocol suffix if present (e.g., '80/tcp' -> '80')
                                    container_port = container_port.split('/')[0]
                                    port_list.append(f"{host_port}->{container_port}")
                    ports = ', '.join(port_list)
                    click.echo(f"{service_name}\t\t{scale}\t{container.short_id}\t{container.name}\t{container.status}\t{ports}")
        
        # Print load balancers
        if lb_containers:
            click.echo("\nLOAD BALANCERS:")
            click.echo("NAME\t\tCONTAINER ID\tSTATUS\t\tPORTS")
            for container in lb_containers:
                port_mappings = container.attrs['NetworkSettings']['Ports']
                port_list = []
                if port_mappings:
                    for container_port, host_bindings in port_mappings.items():
                        if host_bindings:
                            for binding in host_bindings:
                                host_port = binding['HostPort']
                                container_port = container_port.split('/')[0]
                                port_list.append(f"{host_port}->{container_port}")
                ports = ', '.join(port_list)
                click.echo(f"{container.name}\t\t{container.short_id}\t{container.status}\t{ports}")

@click.group()
def main():
    """Orca - A Docker Compose alternative"""
    pass

@main.command()
@click.option('--file', '-f', default='orca.yml', help='Path to Orca configuration file')
@click.option('--rebuild', is_flag=True, help='Force rebuild/pull of images before starting')
@click.argument('service', required=False)
def up(file: str, service: str = None, rebuild: bool = False):
    """Start services"""
    manager = DockerManager()
    manager.load_config(file)
    manager.up(service, rebuild)

@main.command()
@click.argument('service', required=False)
def down(service: str):
    """Stop and remove services"""
    manager = DockerManager()
    manager.load_config('orca.yml')
    manager.down(service)

@main.command()
def ps():
    """List running containers"""
    manager = DockerManager()
    manager.ps()

if __name__ == '__main__':
    main()
