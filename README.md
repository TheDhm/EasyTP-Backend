# EasyTP Backend

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2.6-green)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.16.1-red)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791)](https://www.postgresql.org/)
[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](https://easytp.melekabderrahmane.com)

Django REST Framework backend for **EasyTP Server** - a cloud-native labs & storage management platform deployed on Hetzner Cloud with Kubernetes (k3s).

An updated and enhanced version of the original [EasyTP](https://github.com/TheDhm/EasyTP) project, deployed on Kubernetes with a full CI/CD pipeline.

## Key Features

- **Authentication & Authorization** - JWT-based auth with role-based access control
- **Application Management** - Kubernetes pod lifecycle for containerized apps
- **File Management** - User storage with upload/download capabilities
- **Admin Dashboard** - User activity monitoring and system administration

## Structure

```
├── EasyTPCloud/         # Django project settings
├── api/                 # DRF API endpoints
├── main/                # Core models and business logic
├── shared/              # Shared utilities (files, kubernetes, utils)
├── tests/               # Test suite (unit, integration, API)
└── Dockerfile           # Container build
```

## Related Repositories

- **Frontend**: [EasyTP-Frontend](https://github.com/TheDhm/EasyTP-Frontend)
- **Infrastructure**: [EasyTP-Infra](https://github.com/TheDhm/EasyTP-Infra)
- **Original Monolith**: [EasyTP](https://github.com/TheDhm/EasyTP) (legacy)

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest

# Run development server
python manage.py runserver
```
