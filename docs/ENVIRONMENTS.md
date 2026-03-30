# TactoFlow — Environment Configuration Guide

**Version:** 1.0.0  
**Last Updated:** 2026-03-30

---

## Overview

TactoFlow uses a **branch-based environment strategy** that automatically detects the appropriate configuration based on the current git branch.

| Branch | Environment | Purpose |
|--------|-------------|---------|
| `dev`, `develop`, `feature/*`, `bugfix/*` | **Development** | Local development with hot-reload |
| `staging`, `release/*` | **Staging** | Pre-production testing, QA |
| `main`, `master` | **Production** | Live system serving customers |

---

## Quick Start

### Development (Local)

```bash
# 1. Ensure you're on dev branch
git checkout dev

# 2. Start development environment
./scripts/dev.sh up

# 3. Access the API
curl http://localhost:8100/health
```

### Staging Deployment

```bash
# 1. Switch to staging branch
git checkout staging

# 2. Configure staging secrets
cp config/environments/.env.staging.example config/environments/.env.staging
# Edit with your staging credentials

# 3. Deploy
./scripts/deploy/deploy.sh staging
```

### Production Deployment

```bash
# 1. Switch to main branch
git checkout main

# 2. Configure production secrets (REQUIRED)
cp config/environments/.env.production.example config/environments/.env.production
# Edit with production credentials

# 3. Deploy (requires confirmation)
./scripts/deploy/deploy.sh production
```

---

## Directory Structure

```
tacto-system/
├── config/
│   ├── __init__.py              # Environment detection module
│   └── environments/
│       ├── .env.development     # Dev settings (safe defaults)
│       ├── .env.staging         # Staging settings (gitignored)
│       └── .env.production      # Production settings (gitignored)
├── scripts/
│   ├── dev.sh                   # Development convenience script
│   └── deploy/
│       ├── deploy.sh            # Deployment script
│       └── setup-env.sh         # Environment setup helper
├── docker-compose.unified.yml   # Unified compose with profiles
├── Dockerfile                   # Development image
└── Dockerfile.prod              # Production-optimized image
```

---

## Environment Detection

The system automatically detects the environment using this priority:

1. **`ENVIRONMENT` env var** — Explicit override (highest priority)
2. **Git branch detection** — Automatic based on current branch
3. **Default** — Falls back to `development`

### Python Usage

```python
from config import get_environment, Environment

env = get_environment()

if env == Environment.PRODUCTION:
    # Production-specific logic
    pass
elif env == Environment.STAGING:
    # Staging-specific logic
    pass
else:
    # Development
    pass
```

### Settings Access

```python
from tacto.config.settings import get_settings

settings = get_settings()

# Check environment
if settings.app.is_production:
    print("Running in production!")

# Access environment-specific values
print(f"Environment: {settings.app.environment}")
print(f"Debug: {settings.app.debug}")
```

---

## Environment Variables

### Required by Environment

| Variable | Development | Staging | Production |
|----------|:-----------:|:-------:|:----------:|
| `SECRET_KEY` | Optional (has default) | ✅ Required | ✅ Required |
| `DB_PASSWORD` | Optional (default: tacto) | ✅ Required | ✅ Required |
| `GOOGLE_API_KEY` | ✅ Required | ✅ Required | ✅ Required |
| `JOIN_TOKEN_CLIENTE` | ✅ Required | ✅ Required | ✅ Required |
| `JOIN_WEBHOOK_SECRET` | Optional | Optional | ✅ Required |
| `CORS_ORIGINS` | Optional | Optional | ✅ Required |
| `LANGSMITH_API_KEY` | Optional | Optional | ✅ Required |

### Environment-Specific Defaults

| Setting | Development | Staging | Production |
|---------|-------------|---------|------------|
| `DEBUG` | `true` | `false` | `false` |
| `DB_ECHO` | `true` | `false` | `false` |
| `BYPASS_HOURS_CHECK` | `true` | `false` | `false` |
| `RATE_LIMIT_RPM` | `0` (disabled) | `120` | `60` |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARNING` |
| `DB_POOL_SIZE` | `5` | `5` | `10` |

---

## Docker Compose Profiles

The unified `docker-compose.unified.yml` uses profiles to manage environments:

```bash
# Development (hot-reload, debug mode)
docker compose -f docker-compose.unified.yml --profile dev up

# Staging (production-like)
docker compose -f docker-compose.unified.yml --profile staging up

# Production (optimized)
docker compose -f docker-compose.unified.yml --profile prod up

# Production with Nginx
docker compose -f docker-compose.unified.yml --profile prod --profile prod-nginx up
```

### Service Matrix

| Service | dev | staging | prod |
|---------|:---:|:-------:|:----:|
| `postgres` | ✅ | ✅ | ✅ |
| `redis` | ✅ | ✅ | ✅ |
| `api-dev` | ✅ | ❌ | ❌ |
| `api-staging` | ❌ | ✅ | ❌ |
| `api-prod` | ❌ | ❌ | ✅ |
| `nginx` | ❌ | ❌ | Optional |

---

## Scripts Reference

### `./scripts/dev.sh`

Development environment management:

```bash
./scripts/dev.sh up        # Start containers
./scripts/dev.sh down      # Stop containers
./scripts/dev.sh restart   # Restart API only
./scripts/dev.sh logs      # View API logs
./scripts/dev.sh shell     # Open bash in API container
./scripts/dev.sh migrate   # Run Alembic migrations
./scripts/dev.sh test      # Run pytest
./scripts/dev.sh status    # Show container status
./scripts/dev.sh clean     # Remove all (with confirmation)
```

### `./scripts/deploy/deploy.sh`

Production/Staging deployment:

```bash
./scripts/deploy/deploy.sh staging     # Deploy to staging
./scripts/deploy/deploy.sh production  # Deploy to production (requires confirmation)
```

Features:
- ✅ Pre-deployment validation
- ✅ Automatic database backup
- ✅ Health check after deployment
- ✅ Rollback on failure

---

## Security Checklist

### Before Deploying to Staging

- [ ] `SECRET_KEY` is set and unique
- [ ] `DB_PASSWORD` is not default
- [ ] All API keys are configured
- [ ] `.env.staging` is in `.gitignore`

### Before Deploying to Production

- [ ] All staging checklist items ✅
- [ ] `JOIN_WEBHOOK_SECRET` is configured
- [ ] `CORS_ORIGINS` whitelist is set
- [ ] `LANGSMITH_API_KEY` for observability
- [ ] SSL certificates configured in Nginx
- [ ] Database backups are automated
- [ ] Monitoring/alerting is set up

---

## Troubleshooting

### Environment Not Detected Correctly

```bash
# Check detected environment
python -c "from config import get_environment_info; print(get_environment_info())"

# Force environment
export ENVIRONMENT=production
```

### Database Connection Issues

```bash
# Check if postgres is running
docker ps | grep postgres

# View postgres logs
docker logs tactoflow_postgres_dev

# Test connection
docker exec tactoflow_postgres_dev pg_isready -U tacto
```

### API Not Starting

```bash
# Check API logs
docker logs tactoflow_api_dev

# Check environment file loaded
docker exec tactoflow_api_dev env | grep ENVIRONMENT
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy

on:
  push:
    branches: [main, staging]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set environment
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "ENVIRONMENT=production" >> $GITHUB_ENV
          else
            echo "ENVIRONMENT=staging" >> $GITHUB_ENV
          fi
      
      - name: Deploy
        run: ./scripts/deploy/deploy.sh ${{ env.ENVIRONMENT }}
        env:
          SECRET_KEY: ${{ secrets.SECRET_KEY }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
          # ... other secrets
```

---

## Best Practices

1. **Never commit secrets** — All `.env.*` files (except templates) are gitignored
2. **Use environment detection** — Don't hardcode environment checks
3. **Test in staging first** — Always deploy to staging before production
4. **Backup before deploy** — The deploy script does this automatically
5. **Monitor after deploy** — Check logs and metrics after each deployment
