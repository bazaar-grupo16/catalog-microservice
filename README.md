# Catalog Microservice

Microservicio de catálogo de productos para la plataforma Bazaar. Expone una API REST para crear, consultar y actualizar productos, construida con FastAPI y PostgreSQL.

## Tabla de contenidos

- [Stack](#stack)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Despliegue](#despliegue)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Productos](#productos)
  - [Formato de errores](#formato-de-errores)
- [Arquitectura en capas](#arquitectura-en-capas)

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+, FastAPI, Pydantic, SQLAlchemy |
| Base de datos | PostgreSQL (configurable por env vars) |
| Contenedor | Docker (multi-stage, non-root) |
| Orquestación | Kubernetes (DigitalOcean) |
| CI/CD | GitHub Actions → GHCR → DOKS |

## Estructura del proyecto

```
├── src/
│   ├── api/
│   │   ├── controllers/        # Cableado de dependencias y mapeo request/response
│   │   │   └── product.py      # ProductController: instancia repo y servicio, convierte schemas a DTOs
│   │   ├── routers/            # Registro de rutas — solo delegan al controller
│   │   │   └── product.py      # Rutas de /products
│   │   └── health.py           # /livez y /readyz
│   ├── core/                   # Concerns transversales
│   │   ├── config.py           # Configuración desde variables de entorno
│   │   ├── database.py         # Engine, sesión, base declarativa y retry de conexión
│   │   ├── dependencies.py     # DbSession (Depends reutilizable)
│   │   ├── enums.py            # Enumeraciones compartidas (ProductStatus, ProductSortBy, SortOrder)
│   │   ├── logging.py          # Configuración de logging estructurado
│   │   └── utils.py            # Funciones utilitarias (utc_now)
│   ├── dtos.py                 # Data Transfer Objects internos (dataclasses sin validación)
│   ├── exceptions/             # Excepciones de dominio
│   │   └── product.py          # ProductNotFound
│   ├── models/                 # Entidades SQLAlchemy
│   │   └── product.py          # Product (ORM)
│   ├── repositories/           # Acceso a datos — único lugar que usa Session
│   │   └── product.py          # ProductRepository: find_by_id, find_all, create, save
│   ├── schemas/                # Contratos Pydantic de la API
│   │   ├── product.py          # Request/response schemas de productos
│   │   └── error.py            # ErrorResponse (RFC 7807)
│   ├── services/               # Lógica de negocio pura
│   │   └── product.py          # ProductService: recibe repositorio ya instanciado
│   └── main.py                 # Punto de entrada, registro de routers y exception handlers
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_products.py
├── scripts/
│   ├── run_tests.sh            # Wrapper para correr tests (Linux/macOS)
│   └── run_tests.ps1           # Wrapper para correr tests (Windows)
├── k8s/
│   ├── app-deployment.yaml     # Deployment del microservicio
│   ├── app-service.yaml        # Service (ClusterIP) del microservicio
│   ├── db-deployment.yaml      # Deployment de PostgreSQL
│   ├── db-service.yaml         # Service (ClusterIP) de PostgreSQL
│   ├── db-pvc.yaml             # PersistentVolumeClaim para la BD
│   ├── ingress.yaml            # Ingress Nginx — expone el servicio bajo /catalog
│   └── secret.yaml             # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   ├── ci-dev.yml              # Pipeline de CI en rama dev (lint + tests)
│   └── deploy.yml              # Pipeline de deploy a DOKS en push a main
├── Dockerfile                  # Imagen de producción
├── Dockerfile.test             # Imagen para correr tests
├── docker-compose.yml          # Entorno de desarrollo local (app + PostgreSQL, hot-reload)
├── docker-compose.test.yml     # Levanta PostgreSQL + test runner
├── pyproject.toml              # Configuración de pytest y coverage
├── requirements.txt
└── .env.example
```

## Despliegue

El microservicio se despliega automáticamente en DigitalOcean Kubernetes (DOKS) en cada push a `main` a través del workflow de GitHub Actions (`deploy.yml`). El pipeline construye la imagen Docker, la publica en GHCR y aplica los manifiestos de `k8s/`.

El Ingress de Nginx expone el servicio bajo el prefijo `/catalog`:

```
http://<cluster-host>/catalog/<endpoint>
```

Por ejemplo: `GET http://<cluster-host>/catalog/products`

## Endpoints

### Health

| Método | Path | Descripción | Respuesta exitosa |
|--------|------|-------------|-------------------|
| `GET` | `/livez` | Liveness probe — proceso vivo | `200 {"status": "alive"}` |
| `GET` | `/readyz` | Readiness probe — BD alcanzable | `200 {"status": "ready"}` / `503 {"status": "unavailable"}` |

---

### Productos

#### `POST /products` — Crear producto

**Body JSON:**

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| `title` | string | 1–150 caracteres, no vacío |
| `description` | string | 1–150 caracteres, no vacío |
| `price` | float | ≥ 0.01 |
| `stock` | int | ≥ 0 |
| `category` | string | 1–150 caracteres (se normaliza a minúsculas) |
| `seller_id` | UUID | — |

**Respuesta `201`:**
```json
{
  "data": {
    "id": "uuid",
    "title": "Campera de cuero",
    "description": "Campera negra talle M",
    "price": 150.0,
    "stock": 10,
    "category": "indumentaria",
    "sellerId": "uuid",
    "status": "active",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

---

#### `GET /products` — Listar productos

Por defecto solo devuelve productos activos con stock (`include_inactive=false`).

**Query params:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | int (1–50) | `20` | Cantidad máxima de resultados |
| `offset` | int (≥0) | `0` | Desplazamiento para paginación |
| `search_query` | string | — | Búsqueda por texto libre |
| `category` | string | — | Filtrar por categoría |
| `seller_id` | UUID | — | Filtrar por vendedor |
| `include_inactive` | bool | `false` | Incluir productos inactivos o sin stock |
| `sort_by` | `price` \| `created_at` \| `title` | — | Campo de ordenamiento |
| `order` | `asc` \| `desc` | `asc` | Dirección del ordenamiento |

**Respuesta `200`:**
```json
{
  "data": [ /* array de productos */ ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

#### `GET /products/{id}` — Obtener producto por ID

**Respuesta `200`:** objeto `ProductResponse` (mismo formato que al crear).  
**Respuesta `404`:** error en formato `application/problem+json`.

---

#### `PATCH /products/{id}` — Actualizar producto parcialmente

Solo se modifican los campos presentes en el body.

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| `title` | string | 1–150 caracteres, no vacío |
| `description` | string | 1–150 caracteres, no vacío |
| `price` | float | ≥ 0.01 |
| `stock` | int | ≥ 0 |
| `category` | string | 1–150 caracteres (se normaliza a minúsculas) |
| `status` | `active` \| `inactive` | — |

**Respuesta `200`:** objeto `ProductResponse` con los datos actualizados.  
**Respuesta `404`:** error en formato `application/problem+json` si el producto no existe.

---

### Formato de errores

Todos los errores de dominio siguen [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807) con `Content-Type: application/problem+json`:

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Product not found",
  "instance": "/products/550e8400-e29b-41d4-a716-446655440000"
}
```

## Arquitectura en capas

El proyecto sigue una arquitectura en capas con dependencias unidireccionales:

```
HTTP Request
    │
    ▼
Router          — registra rutas, delega al controller
    │
    ▼
Controller      — instancia Repository(db) y Service(repo), convierte schemas → DTOs
    │
    ▼
Service         — lógica de negocio pura, recibe repositorio inyectado, lanza excepciones de dominio
    │
    ▼
Repository      — único lugar que construye queries SQL, usa self.db
    │
    ▼
PostgreSQL
```

**Regla de dependencias:** cada capa solo conoce a la inmediatamente inferior. El servicio no importa nada de `src.schemas` ni de FastAPI. Los routers no tienen lógica de negocio ni acceso a base de datos.

**DTOs (`src/dtos.py`):** dataclasses sin validación que transportan datos entre el controller y el servicio. La validación ocurre en los schemas de Pydantic antes de construir el DTO.

**Excepciones de dominio (`src/exceptions/`):** el servicio lanza `ProductNotFound` (y similares a futuro) en lugar de devolver `None`. `main.py` registra un handler global que serializa estas excepciones a `application/problem+json` según RFC 7807.
