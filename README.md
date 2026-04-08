# Catalog Microservice

Base inicial para el microservicio `catalog-service`, construido sobre el template de microservicios con FastAPI y PostgreSQL.

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.11+, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | PostgreSQL (configurable por env vars) |
| Contenedor | Docker (multi-stage, non-root) |
| Orquestación | Kubernetes (DigitalOcean) |
| CI/CD | GitHub Actions → GHCR → DOKS |

## Estructura del proyecto

```
├── src/
│   ├── api/            # Routers de FastAPI
│   │   └── health.py   # /livez y /readyz
│   ├── core/           # Configuración, DB, logging
│   │   ├── config.py
│   │   ├── database.py  # Engine, sesión, base, y retry de conexión
│   │   ├── dependencies.py
│   │   └── logging.py
│   ├── models/         # Entidades SQLAlchemy del dominio
│   ├── schemas/        # Modelos Pydantic del dominio
│   ├── services/       # Lógica de negocio
│   └── main.py         # Punto de entrada
├── tests/
│   ├── conftest.py
│   └── test_health.py
├── scripts/
│   ├── run_tests.sh    # Wrapper para correr tests (Linux/macOS)
│   └── run_tests.ps1   # Wrapper para correr tests (Windows)
├── k8s/
│   ├── app-deployment.yaml   # Deployment del microservicio
│   ├── app-service.yaml      # Service (ClusterIP) del microservicio
│   ├── db-deployment.yaml    # Deployment de PostgreSQL
│   ├── db-service.yaml       # Service (ClusterIP) de PostgreSQL
│   ├── db-pvc.yaml           # PersistentVolumeClaim para la BD
│   └── secret.yaml           # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   └── deploy.yml
├── Dockerfile              # Imagen de producción
├── Dockerfile.test         # Imagen para correr tests
├── docker-compose.test.yml # Levanta PostgreSQL + test runner
├── requirements.txt
└── .env.example
```

## Setup local

```bash
# 1. Clonar y entrar al directorio
git clone https://github.com/bazaar-grupo16/catalog-microservice.git && cd catalog-microservice

# 2. Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con las credenciales de tu base de datos local

# 5. Levantar la aplicación
uvicorn src.main:app --reload
```

## Conectarse al cluster de DigitalOcean

Requisitos:
- Tener instalado [doctl](https://docs.digitalocean.com/reference/doctl/)
- Tener instalado [kubectl](https://kubernetes.io/docs/tasks/tools/)

```bash
# 1. Iniciar sesión en doctl
doctl auth init --context <NAME>
doctl auth switch --context <NAME>

# 2. Obtener credenciales del cluster
doctl kubernetes cluster kubeconfig save <CLUSTER_ID>
```

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/livez` | Liveness probe — siempre 200 |
| GET | `/readyz` | Readiness probe — verifica conexión a DB |
| POST | `/products` | Crear producto |
| GET | `/products` | Listar productos con paginación y filtros |
| GET | `/products/{product_id}` | Ver detalle de producto |
| PUT | `/products/{product_id}` | Reemplazar producto |
| PATCH | `/products/{product_id}/status` | Activar o desactivar producto |
| GET | `/docs` | Swagger UI (auto-generado) |
| GET | `/redoc` | ReDoc (auto-generado) |

## Tests

Los tests corren contra una **base de datos PostgreSQL real** usando Docker Compose. No se usa mocking.

El archivo `docker-compose.test.yml` levanta:
1. Un contenedor **PostgreSQL 16** como base de datos.
2. Un contenedor **test-runner** que ejecuta `pytest` contra esa base de datos.

### Correr los tests

```bash
# Linux / macOS
./scripts/run_tests.sh

# Windows (PowerShell)
.\scripts\run_tests.ps1

# O directamente con docker compose
docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

> Los contenedores se limpian automáticamente al finalizar.

## Docker

```bash
docker build -t catalog-service .
docker run -p 8000:8000 --env-file .env catalog-service
```

## Kubernetes

Los manifiestos en `k8s/` despliegan el microservicio junto con su propia base de datos PostgreSQL dentro del cluster.

### Variables de entorno requeridas (GitHub Secrets)

| Secret | Descripción |
|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | Personal Access Token de DigitalOcean |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_NAME` | Nombre de la base de datos |

`DB_HOST` y `DB_PORT` están fijos en `k8s/secret.yaml` (`bazaar-db:5432`) ya que la BD corre dentro del cluster.
Si se utilizase una base de datos externa, se deberían agregar las variables de entorno correspondientes.

### Deploy manual

```bash
# Crear el namespace (solo la primera vez)
kubectl create namespace bazaar-dev

# Aplicar todos los manifiestos en orden
kubectl apply -f k8s/db-pvc.yaml       -n bazaar-dev
kubectl apply -f k8s/db-deployment.yaml -n bazaar-dev
kubectl apply -f k8s/db-service.yaml    -n bazaar-dev
kubectl apply -f k8s/secret.yaml        -n bazaar-dev
kubectl apply -f k8s/app-deployment.yaml -n bazaar-dev
kubectl apply -f k8s/app-service.yaml   -n bazaar-dev
```

### CI/CD automático

El pipeline en `.github/workflows/deploy.yml` corre automáticamente en cada push a `main`:

| Job | Se ejecuta cuando cambia... |
|-----|----------------------------|
| `lint` | `src/`, `tests/`, archivos de build |
| `test` | `src/`, `tests/`, archivos de build |
| `build` | `src/`, `tests/`, archivos de build (solo push a main) |
| `deploy` | `src/` **o** `k8s/` (solo push a main) |

## Conexión a la base de datos

Al iniciar, la aplicación espera a que la base de datos esté disponible usando **backoff exponencial** (1s → 2s → 4s → … hasta 30s por intento, máximo 5 minutos en total) antes de ejecutar las migraciones y aceptar tráfico. Esto evita crasheos durante el arranque del pod cuando la BD aún está inicializándose.

## CRUD de productos

El servicio expone una primera base funcional de catálogo con:

- persistencia propia en PostgreSQL;
- soft delete mediante `status=inactive`;
- visibilidad pública por default solo para productos `active` con `stock > 0`;
- detalle visible para productos activos aunque tengan `stock = 0`;
- búsqueda por texto en `title` y `description` con prioridad de matches en `title`;
- filtros opcionales por `category` y `seller_id`;
- paginación simple por `limit` y `offset`.

### Ejemplo de creación

```json
{
  "title": "Mechanical Keyboard",
  "description": "Compact keyboard with tactile switches",
  "price": 129.90,
  "stock": 8,
  "category": "peripherals",
  "seller_id": "6bf5e4aa-18e2-4ff8-a7a4-b87c60567b83"
}
```

### Reglas principales

- `GET /products` devuelve por default solo productos activos con stock.
- `GET /products?search_query=keyboard` busca coincidencias parciales case-insensitive en `title` y `description`.
- Cuando una búsqueda matchea en ambos campos, se priorizan primero los resultados con match en `title` y luego se desempata por `created_at desc`.
- `GET /products/{product_id}` oculta productos inactivos salvo que se use `include_inactive=true`.
- `GET /products/{product_id}` devuelve `404` si el producto no existe.
- `PATCH /products/{product_id}/status` permite publicar o despublicar sin borrar físicamente el registro.

### Ejemplos de consultas

```bash
curl "http://localhost:8000/products?limit=12&offset=0"
curl "http://localhost:8000/products?search_query=keyboard"
curl "http://localhost:8000/products?search_query=monitor&category=peripherals"
curl "http://localhost:8000/products/<product_id>"
```
