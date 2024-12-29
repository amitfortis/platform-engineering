# platform-engineering
# Kubernetes Management UI

A lightweight web interface for managing Kubernetes clusters. Built with Python Flask and Kubernetes API, this tool provides a simple way to manage namespaces, deployments, and monitor cluster resources.

## Features

- Create and manage namespaces
- Deploy applications with container image and port configuration
- View pod and service status
- Reset or remove namespaces and their resources
- Real-time cluster status monitoring

## Tech Stack

- **Backend**: Python Flask, Kubernetes Python Client
- **Frontend**: HTML, JavaScript, Tailwind CSS
- **Deployment**: Docker, Kubernetes
- **Server**: Gunicorn WSGI

## Quick Start

1. Deploy to your Kubernetes cluster:
```bash
kubectl apply -f k8s-ui.yaml
```

2. Access the UI:
```bash
# Get the NodePort service port
kubectl get svc -n k8s-ui
```

## Security

The application runs with a ServiceAccount that has controlled RBAC permissions:
- Namespace management
- Pod and service operations
- Deployment controls

## Project Structure

```
├── app.py              # Flask application with K8s API integration
├── Dockerfile          # Multi-stage build for optimized image
├── k8s-ui.yaml        # Kubernetes deployment manifests
├── wsgi.py            # WSGI entry point
└── templates/
    └── index.html     # Web interface
```

## Notes

- The UI excludes system namespaces (kube-system, kube-public, kube-node-lease)
- Container images must follow the format: repository/image:tag
- Port range: 1-65535

## Requirements

- Kubernetes cluster
- RBAC permissions for namespace management
- Container runtime (Docker/containerd)
