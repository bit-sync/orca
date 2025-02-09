---
layout: default
title: Getting Started
nav_order: 2
---

# Getting Started with Orca

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/orca.git
   cd orca
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

### Start Services
```bash
./orca.py up
```

### Stop Services
```bash
./orca.py down
```

### View Status
```bash
./orca.py status
```

## Creating Your First Configuration

1. Create an `orca.yml` file in your project directory:

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

2. Create a simple HTML file:

```bash
mkdir html
echo '<h1>Hello from Orca!</h1>' > html/index.html
```

3. Start your services:

```bash
./orca.py up
```

4. Visit `http://localhost:8080` to see your web service in action!
