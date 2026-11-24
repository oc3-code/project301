# estore (project301)

A Django REST API for a small e-commerce store (users, products, orders, shipments),
containerised with Docker and deployed to Kubernetes (AKS) with a PostgreSQL backend.

## Tech stack

- Python 3.9, Django 3.2.2, Django REST Framework 3.12.4
- PostgreSQL (local: `postgres:13.2-alpine`; cloud: Azure Database for PostgreSQL)
- `python-decouple` for configuration, `gunicorn` as the production server
- Docker / Docker Compose for local development
- Azure Container Registry + Azure Kubernetes Service for deployment

## Project layout

```
project301/
├── app/                      Django project
│   ├── estore/               settings, root URLs, WSGI
│   ├── api/                  models, serializers, views, URLs, tests, migrations
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env                  local settings (not used inside the cluster)
├── data/                     Postgres init scripts for Docker Compose
├── docker-compose.yml        local stack: web + Postgres + pgAdmin
├── estore-deployment.yml     Kubernetes Deployment + LoadBalancer Service
└── DEPLOYMENT_ISSUES.md      problems met during deployment and their fixes
```

## Data model

| Model | Key fields |
|---|---|
| `UserType` | `code` (unique), `description` |
| `User` | `name`, `login` (unique), `password`, `user_type` (FK) |
| `Product` | `sku` (unique), `description`, `unit_price` |
| `Order` | `created`, `user` (FK) |
| `OrderProduct` | `order` (FK), `product` (FK), `quantity`, `sale_price`; unique per (order, product) |
| `Shipment` | `carrier`, `tracking_number`, `shipped`, `order` (one-to-one) |

## API endpoints

All routes are under `/api/`. List routes accept `GET` and `POST`; detail routes
support retrieve, update and delete.

| Resource | List / create | Detail |
|---|---|---|
| User types | `usertype/` | `usertype/<id>` |
| Users | `user/` | `user/<id>` |
| Products | `product/` | `product/<id>` |
| Orders | `order/` | `order/<id>` |
| Order products | `orderproduct/` | `orderproduct/<id>` |
| Order items by order | `orderproduct/order/<order_id>` | |
| Order item by keys | | `orderproduct/order/<order_id>/product/<product_id>` |
| Shipments | `shipment/` | `shipment/<id>` |

## Configuration

Settings are read with `python-decouple`: environment variables first, then `app/.env`.

| Variable | Purpose |
|---|---|
| `DB_NAME` | Database name |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port (`5432`) |

Missing variables stop Django at startup with `UndefinedValueError`.

## Run locally

### With Docker Compose

```
docker compose up --build
docker compose exec web python manage.py migrate
```

The API is at http://localhost:8000/api/ and pgAdmin at http://localhost:5433.

### Without Docker

```
cd app
python -m venv venv && venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Requires a reachable PostgreSQL instance matching the values in `app/.env`.

### Tests

```
cd app
python manage.py test
```

## Deploy to Kubernetes

1. **Create migrations locally** and commit them. Do not run `makemigrations` inside a pod,
   because the files are lost on restart.
   ```
   python manage.py makemigrations
   ```
2. **Build and push the image** with a new tag each time the code changes:
   ```
   docker build -t estoreregistry.azurecr.io/estore:<tag> ./app
   docker push estoreregistry.azurecr.io/estore:<tag>
   ```
3. **Set the image tag** in `estore-deployment.yml`, then apply:
   ```
   kubectl apply -f estore-deployment.yml
   kubectl rollout status deploy/estore
   ```
4. **Run migrations** against the database:
   ```
   kubectl exec deploy/estore -- python manage.py migrate
   ```
5. **Find the public IP** and test:
   ```
   kubectl get svc estore-service
   curl http://<EXTERNAL-IP>:8000/api/product/
   ```

The Deployment's `env:` block must define `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`
and `DB_PORT`. Django's `ALLOWED_HOSTS` must include the LoadBalancer IP, or requests
fail with `DisallowedHost`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `UndefinedValueError: DB_NAME not found` | Env var names in the manifest don't match `settings.py` | Use `DB_*` names and add `DB_PORT` |
| `PermissionError` writing `api/migrations/...` | Non-root user, or stale image | Generate migrations locally; rebuild the image |
| `DisallowedHost` | IP missing from `ALLOWED_HOSTS` | Add the LoadBalancer IP |
| `relation "..." does not exist` | Migrations not applied | Run `migrate` in the pod |

Full details are in [DEPLOYMENT_ISSUES.md](DEPLOYMENT_ISSUES.md).

## Security notes

- Don't commit database passwords. Keep them in a Kubernetes Secret (`secretKeyRef`)
  instead of plain text in `estore-deployment.yml`, and rotate any that were exposed.
- Set `DEBUG` to `False` and restrict `ALLOWED_HOSTS` before exposing the service publicly.
- For production, remove the `runserver` args from the Deployment so the image's gunicorn
  `CMD` is used.
