---
layout: default
title: Configuration
nav_order: 3
---

# Configuration Guide

## Overview

Orca uses a YAML configuration file (`orca.yml`) to define services and load balancers. The configuration is designed to be intuitive and easy to understand.

## Configuration Structure

```yaml
services:
  service_name:
    image: image_name
    scale: number_of_instances
    ports:
      - container_port
    volumes:
      - host_path:container_path
    environment:
      - KEY=value

load_balancers:
  balancer_name:
    services:
      - name: service_name
        weight: traffic_weight
    port: host_port
    algorithm: balancing_algorithm
```

## Service Configuration

### Required Fields
- `image`: Docker image to use

### Optional Fields
- `scale`: Number of instances (default: 1)
- `ports`: List of container ports to expose
- `volumes`: List of volume mappings
- `environment`: List of environment variables

### Example
```yaml
services:
  web:
    image: nginx:latest
    scale: 3
    ports:
      - 80
    volumes:
      - ./html:/usr/share/nginx/html
```

## Load Balancer Configuration

### Required Fields
- `services`: List of services to load balance
  - `name`: Service name to balance
- `port`: Port to expose on host

### Optional Fields
- `algorithm`: Load balancing algorithm (default: round_robin)
  - Options: round_robin, least_conn
- `services[].weight`: Traffic weight for service (default: 1)

### Example
```yaml
load_balancers:
  web_lb:
    services:
      - name: web
        weight: 1
    port: 8080
    algorithm: round_robin
```
