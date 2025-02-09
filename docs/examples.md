---
layout: default
title: Examples
nav_order: 5
---

# Examples

## Basic Web Service

A simple web service with a single instance:

```yaml
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

## Scaled Web Service

Web service with multiple instances for high availability:

```yaml
services:
  web:
    image: nginx:latest
    scale: 3
    volumes:
      - ./html:/usr/share/nginx/html

load_balancers:
  web_lb:
    services:
      - name: web
    port: 8080
```

## Web Service with Redis

Web service with a Redis backend:

```yaml
services:
  api:
    image: your-api-image:latest
    scale: 3
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379

  redis:
    image: redis:latest
    ports:
      - 6379

load_balancers:
  api_lb:
    services:
      - name: api
    port: 8080
```

## Multiple Load Balancers

Multiple services with separate load balancers:

```yaml
services:
  web:
    image: nginx:latest
    scale: 2

  api:
    image: your-api-image:latest
    scale: 2

load_balancers:
  web_lb:
    services:
      - name: web
    port: 8080

  api_lb:
    services:
      - name: api
    port: 8081
```

## Weighted Load Balancing

Load balancing with traffic weight distribution:

```yaml
services:
  web_v1:
    image: web-app:v1
    scale: 2

  web_v2:
    image: web-app:v2
    scale: 1

load_balancers:
  web_lb:
    services:
      - name: web_v1
        weight: 2
      - name: web_v2
        weight: 1
    port: 8080
```
