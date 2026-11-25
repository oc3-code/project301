# estore (project301)

A Django REST API for a small e-commerce store (user types, users, products, orders,
order items and shipments). It runs locally with Docker Compose and is deployed to
Azure Kubernetes Service (AKS) with an Azure Database for PostgreSQL backend.

## Tech stack

- Python 3.9, Django 3.2.2, Django REST Framework 3.12.4
- PostgreSQL (local: `postgres:13.2-alpine`; cloud: Azure Database for PostgreSQL Flexible Server)
- `python-decouple` for configuration, `gunicorn` as the image's default server
- Docker / Docker Compose for local development
- Azure Container Registry (ACR) + Azure Kubernetes Service (AKS) for deployment

## Project layout

```
project301/
├── app/                          Django project
│   ├── estore/                   settings, root URLs (admin/, api/), WSGI
│   ├── api/                      models, serializers, views, URLs, tests
│   │   └── migrations/           0001_initial.py (committed)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env                      local settings (DB_* variables)
├── data/django_init.sql          Postgres init script (creates estore_db)
├── doc/
│   ├── azure-deployment-notes.docx   step-by-step Azure/AKS deployment record
│   ├── estore-pg-ERD.png             entity-relationship diagram
│   └── estore.drawio                 editable source of the diagram
├── docker-compose.yml            local stack: web + Postgres + pgAdmin
└── estore-deployment.yml         Kubernetes Deployment + LoadBalancer Service
```

## Data model

The ERD is in [doc/estore-pg-ERD.png](doc/estore-pg-ERD.png) (editable source:
[doc/estore.drawio](doc/estore.drawio)).

| Model | Key fields |
|---|---|
| `UserType` | `code` (unique), `description` |
| `User` | `name`, `login` (unique), `password` (hashed on create/update, never returned), `user_type` (FK) |
| `Product` | `sku` (unique), `description`, `unit_price` (decimal, 2 places) |
| `Order` | `created`, `user` (FK) |
| `OrderProduct` | `order` (FK), `product` (FK), `quantity`, `sale_price`; unique per (order, product) |
| `Shipment` | `carrier`, `tracking_number`, `shipped`, `order` (one-to-one) |

Deleting a user type that is in use, or a user that has orders, is rejected (protected
foreign keys).

## API endpoints

All routes are under `/api/`. List routes support `GET` and `POST`; detail routes support
`GET`, `PUT`, `PATCH` and `DELETE`.

| Resource | List / create | Detail |
|---|---|---|
| User types | `usertype/` | `usertype/<id>` |
| Users | `user/` | `user/<id>` |
| Products | `product/` | `product/<id>` |
| Orders | `order/` | `order/<id>` |
| Order products | `orderproduct/` | `orderproduct/<id>` |
| Items of one order | `orderproduct/order/<order_id>` | |
| Item by order and product | | `orderproduct/order/<order_id>/product/<product_id>` |
| Shipments | `shipment/` | `shipment/<id>` |

The Django admin is at `/admin/`.

## Configuration

Settings are read by `python-decouple`: environment variables first, then `app/.env`.

| Variable | Purpose |
|---|---|
| `DB_NAME` | Database name (`estore_db`) |
| `DB_USER` | Database user |
| `DB_PASSWORD` | Database password |
| `DB_HOST` | Database host |
| `DB_PORT` | Database port (`5432`) |

A missing variable stops Django at startup with `UndefinedValueError`.
`ALLOWED_HOSTS` is currently `['*']` and `DEBUG` is `True` in `settings.py`.

## Run locally

### With Docker Compose

```
docker compose up --build
docker compose exec web python manage.py migrate
```

- API: http://localhost:8000/api/
- pgAdmin: http://localhost:5433 (login and passwords are in `docker-compose.yml`)

### Without Docker

```
cd app
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Needs a reachable PostgreSQL instance matching `app/.env`.

### Tests

```
cd app
python manage.py test
```

`api/tests.py` covers every resource: list, create, validation errors, duplicates,
retrieve/404, PUT/PATCH, delete and protected deletes, and password hashing.

## Deploy to Azure Kubernetes Service

The full record, including the commands used, is in
[doc/azure-deployment-notes.docx](doc/azure-deployment-notes.docx). Summary:

**Azure resources**

| Resource | Name |
|---|---|
| Resource group | `estoreresgroup` |
| Container registry | `estoreregistry` (`estoreregistry.azurecr.io`) |
| AKS cluster | `estorecluster` (ACR attached with `az aks update --attach-acr`) |
| PostgreSQL Flexible Server | `estore-server`, database `estore_db` |

**Steps**

1. Create the resource group, ACR, AKS cluster and PostgreSQL server, then create `estore_db`.
2. Connect to the cluster:
   ```
   az aks get-credentials --resource-group estoreresgroup --name estorecluster
   az acr login --name estoreregistry
   ```
3. Create migrations **locally** and commit them (never inside a pod; the files are lost on restart):
   ```
   python manage.py makemigrations
   ```
4. Build, tag and push the image (use a new tag for each code change):
   ```
   cd app
   docker build -t estore .
   docker tag estore:latest estoreregistry.azurecr.io/estore:v4
   docker push estoreregistry.azurecr.io/estore:v4
   ```
5. Check `estore-deployment.yml` (image tag, `DB_*` values), then deploy:
   ```
   kubectl apply -f estore-deployment.yml
   kubectl get pods
   kubectl get services
   ```
6. Apply migrations to the database from the pod:
   ```
   kubectl exec <pod-name> -- python manage.py migrate
   ```
7. Test with the service's `EXTERNAL-IP`: `http://<EXTERNAL-IP>:8000/api/product/`.

The Deployment passes `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` and `DB_PORT` as
environment variables, and the `LoadBalancer` Service exposes port 8000.

Useful commands: `kubectl logs <pod-name>`, `kubectl get deployments`,
`kubectl delete deployment estore`, `kubectl delete service estore-service`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `UndefinedValueError: DB_NAME not found` | Env var names in the manifest didn't match `settings.py` (`DATABASE_*` vs `DB_*`), and `DB_PORT` was missing | Use the `DB_*` names and add `DB_PORT` |
| `PermissionError` writing `api/migrations/...` in the pod | `makemigrations` run in the container as non-root user | Run `makemigrations` locally, commit, rebuild the image, run only `migrate` in the pod |
| `DisallowedHost` for the LoadBalancer IP | IP missing from `ALLOWED_HOSTS` | Added `'*'` (restrict for production) |
| `relation "..." does not exist` | Migrations not applied | Run `migrate` in the pod |
| Connection or auth errors to Azure Postgres | SSL is enforced by default | Add `OPTIONS: {'sslmode': 'require'}` to `DATABASES` |

## Known limitations and security notes

- **Credentials in plain text.** `estore-deployment.yml` holds the database user and password
  as literal values, and `doc/azure-deployment-notes.docx` contains the server's connection
  string with its password. Don't push either to a public repository as is. Move the values
  into a Kubernetes Secret (`secretKeyRef`), remove them from the notes, and rotate the password.
- **`ALLOWED_HOSTS = ['*']` and `DEBUG = True`** are for the class project only. Set explicit hosts
  and `DEBUG = False` (for example via `config('DEBUG', default=False, cast=bool)`) before real use.
- **Dev server in the cluster.** The Deployment's `args` run `manage.py runserver`, overriding the
  image's gunicorn `CMD`. For production remove `args`; gunicorn then needs a static files
  solution such as whitenoise.
- **Compose init script path.** `docker-compose.yml` mounts `./data/misc/django_init.sql`, but the
  script lives at `data/django_init.sql`, so the init script isn't applied locally. The `web` service
  doesn't create `estore_db` by itself beyond the `POSTGRES_DB` setting, which does cover it.
- The API has no authentication or permission classes configured.
