---
layout: default
title: Load Balancing
nav_order: 4
---

# Load Balancing

## Overview

Orca provides built-in load balancing capabilities using Nginx. The load balancer is automatically configured based on your service definitions and can handle service scaling and health monitoring.

## Features

- Round-robin and least connections algorithms
- Passive health monitoring
- Automatic failover
- Connection handling optimizations
- Health check endpoint at `/health`

## Configuration

### Basic Configuration
```yaml
load_balancers:
  web_lb:
    services:
      - name: web
    port: 8080
```

### Advanced Configuration
```yaml
load_balancers:
  web_lb:
    services:
      - name: web
        weight: 2
      - name: web_backup
        weight: 1
    port: 8080
    algorithm: least_conn
```

## Load Balancing Algorithms

### Round Robin (default)
Requests are distributed evenly across all servers in sequence.

```yaml
algorithm: round_robin
```

### Least Connections
Requests are distributed to the server with the least active connections.

```yaml
algorithm: least_conn
```

## Health Monitoring

### Passive Health Checks
The load balancer automatically monitors backend health:
- Detects failed connections
- Removes unhealthy instances
- Retries failed requests
- Returns instances after recovery

### Health Check Endpoint
Each load balancer provides a `/health` endpoint:
```bash
curl http://localhost:8080/health
```

## Connection Settings

The load balancer is configured with optimized connection settings:
- Connection pooling
- Keep-alive connections
- Proxy buffering
- Timeouts and retries

## Scaling

When scaling services, the load balancer automatically:
1. Detects new instances
2. Adds them to the upstream pool
3. Starts directing traffic
4. Maintains existing connections
