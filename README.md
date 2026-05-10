# Catalog Microservice

Microservicio de catálogo de productos para la plataforma Bazaar. Expone una API REST para crear, consultar, actualizar y eliminar productos, construida con FastAPI y PostgreSQL. La gestión de stock se delega al **inventory service**.

## Tabla de contenidos

- [Stack](#stack)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Autenticación](#autenticación)
- [Despliegue](#despliegue)
- [Endpoints](#endpoints)
  - [Health](#health)
  - [Productos](#productos)
  - [Formato de errores](#formato-de-errores)
- [Arquitectura en capas](#arquitectura-en-capas)
- [Integración con inventory service](#integración-con-inventory-service)

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
│   │   ├── dependencies.py     # DbSession y UserID (Depends reutilizables)
│   │   ├── enums.py            # Enumeraciones compartidas (ProductStatus, ProductSortBy, SortOrder)
│   │   ├── logging.py          # Configuración de logging estructurado
│   │   └── utils.py            # Funciones utilitarias (utc_now)
│   ├── dtos.py                 # Data Transfer Objects internos (dataclasses sin validación)
│   ├── exceptions/             # Excepciones de dominio
│   │   └── product.py          # ProductNotFound, ImageNotFound, ImageValidationError, etc.
│   ├── models/                 # Entidades SQLAlchemy
│   │   └── product.py          # Product (ORM)
│   ├── repositories/           # Acceso a datos — único lugar que usa Session
│   │   └── product.py          # ProductRepository: find_by_id, find_all, create, save
│   ├── schemas/                # Contratos Pydantic de la API
│   │   ├── product.py          # Request/response schemas de productos
│   │   └── error.py            # ErrorResponse (RFC 7807)
│   ├── services/               # Lógica de negocio pura
│   │   ├── product.py          # ProductService: orquesta repo, storage e inventory
│   │   ├── storage.py          # StorageService: cliente S3/DigitalOcean Spaces
│   │   └── inventory.py        # InventoryService: cliente del inventory service (stub)
│   └── main.py                 # Punto de entrada, registro de routers y exception handlers
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_products.py
│   └── test_images.py
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

## Autenticación

El API Gateway (NGINX Ingress) valida el JWT del cliente y propaga el ID del usuario autenticado como header interno `X-User-ID: <uuid>`. Este microservicio **no procesa JWTs directamente** — solo lee ese header cuando lo necesita.

Los endpoints que requieren autenticación validan que el header esté presente y sea un UUID válido. Si no lo es, devuelven `401` en formato `application/problem+json`. Los endpoints públicos no requieren el header.

| Visibilidad | Endpoints |
|-------------|-----------|
| **Públicos** (sin auth) | `GET /products`, `GET /products/{id}`, `GET /products/{id}/share-link`, `GET /livez`, `GET /readyz`, `PATCH /internal/products/{id}/stock-status` |
| **Autenticados** (requieren `X-User-ID`) | `POST /products`, `GET /products/me`, `PATCH /products/{id}`, `DELETE /products/{id}`, y todos los endpoints de imágenes |

El Ingress de Nginx está dividido en dos recursos:
- **`catalog-public-ingress`**: enruta los paths públicos sin pasar por el servicio de autenticación.
- **`catalog-ingress`**: enruta todo lo demás bajo `/catalog`, configurado con `auth-url` para que NGINX valide el JWT antes de forwwardear la request y agregue el header `X-User-ID`.

## Despliegue

El microservicio se despliega en DigitalOcean Kubernetes (DOKS) mediante el workflow de GitHub Actions `.github/workflows/deploy.yml`. El workflow valida pushes a `main`, pull requests contra `main` y ejecuciones manuales (`workflow_dispatch`); el deploy a Kubernetes se ejecuta en pushes a `main` o en ejecuciones manuales con `run_deploy=true`.

El flujo de CI/CD ejecuta:

1. Lint con Ruff sobre `src/` y `tests/`.
2. SAST con Bandit sobre `src/`.
3. Tests con PostgreSQL real mediante `docker compose -f docker-compose.test.yml`.
4. Build y push de la imagen Docker a GHCR con los tags `${{ github.sha }}` y `latest`.
5. Deploy a Kubernetes con `kubectl apply`; los manifiestos de `k8s/` se procesan previamente con `envsubst`.

La app corre dentro del contenedor en el puerto `8000`. El `Service` interno la publica dentro del cluster y el Ingress de Nginx expone el acceso HTTP externo.

El Ingress está dividido en dos recursos (ver `k8s/ingress.yaml`):

- **`catalog-public-ingress`**: expone sin autenticación los paths de solo lectura (`/catalog/products`, `/catalog/products/{id}`, `/catalog/products/{id}/share-link`).
- **`catalog-ingress`**: expone todo lo demás bajo `/catalog` con autenticación delegada al auth-service.

Ambos reescriben el prefijo `/catalog` antes de forwwardear al pod:

```
http://<cluster-host>/catalog/<endpoint>
```

Por ejemplo: `GET http://<cluster-host>/catalog/products`

Las variables de base de datos, Spaces y `PUBLIC_APP_BASE_URL` se inyectan desde secretos de Kubernetes. `INVENTORY_SERVICE_URL` se define en el deployment como `http://inventory-service`.

## Endpoints

### Health

| Método | Path | Descripción | Respuesta exitosa |
|--------|------|-------------|-------------------|
| `GET` | `/livez` | Liveness probe — proceso vivo | `200 {"status": "alive"}` |
| `GET` | `/readyz` | Readiness probe — BD alcanzable | `200 {"status": "ready"}` / `503 {"status": "unavailable"}` |

---

### Productos

#### `POST /products` — Crear producto

Crea el producto en catalog y registra su stock inicial en el inventory service.

**Body (multipart/form-data):**

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| `title` | string | 1–150 caracteres, no vacío |
| `description` | string | mínimo 1 carácter, no vacío |
| `price` | float | ≥ 0.01 |
| `stock` | int | ≥ 0 — se envía al inventory service |
| `category` | string | 1–80 caracteres (se normaliza a minúsculas) |
| `files` | imágenes | Al menos una imagen (JPEG, PNG o WebP, máx. 10 MB c/u) |

Si el producto se crea con `stock=0`, queda en estado `out_of_stock` desde el inicio. Si se crea con `stock>0`, queda `active`.

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

#### `GET /products/me` — Mis productos

Devuelve todas las publicaciones del vendedor autenticado, **incluyendo** productos con status `inactive` o `out_of_stock` (el vendedor ve su catálogo completo).

**Query params:** `limit`, `offset`, `search_query`, `sort_by`, `order` (mismos que `GET /products`).

**Respuesta `200`:** mismo formato que `GET /products`.  
**Respuesta `401`:** si falta el header o el UUID es inválido.

---

#### `GET /products` — Listar productos

Devuelve los productos actualmente visibles en el catálogo público. El campo `stock` de cada producto se obtiene del inventory service. Los productos sin stock (`out_of_stock`) o deshabilitados (`inactive`) no se incluyen, salvo que se use `include_inactive=true`.

**Query params:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `limit` | int (1–50) | `20` | Cantidad máxima de resultados |
| `offset` | int (≥0) | `0` | Desplazamiento para paginación |
| `search_query` | string | — | Búsqueda por texto libre en título y descripción. Soporta búsqueda fuzzy (tolerante a errores tipográficos) vía `pg_trgm`: las coincidencias exactas tienen prioridad, seguidas de coincidencias aproximadas (similarity > 0.3) |
| `category` | string | — | Filtrar por categoría |
| `seller_id` | UUID | — | Filtrar por vendedor |
| `include_inactive` | bool | `false` | Incluir productos con status `inactive` |
| `sort_by` | `price` \| `created_at` \| `title` | — | Campo de ordenamiento |
| `order` | `asc` \| `desc` | `asc` | Dirección del ordenamiento |
| `min_price` | float (> 0) | — | Precio mínimo inclusivo |
| `max_price` | float (> 0) | — | Precio máximo inclusivo |

Si `search_query` se usa sin `sort_by`, el orden prioriza relevancia: coincidencia exacta en título, coincidencia exacta en descripción, coincidencia fuzzy en título, coincidencia fuzzy en descripción, y luego fecha de creación descendente. Si se especifica `sort_by`, ese orden explícito reemplaza el orden por relevancia.

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

El `stock` devuelto se consulta en tiempo real al inventory service.

Un producto `out_of_stock` sigue siendo consultable por ID para mostrar su detalle, aunque no aparezca en el listado público.

**Respuesta `200`:** objeto `ProductResponse` (mismo formato que al crear).  
**Respuesta `404`:** error en formato `application/problem+json`.

---

#### `GET /products/{id}/share-link` — Obtener link compartible de un producto

Devuelve una URL pública que apunta directamente al detalle del producto, lista para copiar y compartir fuera de la plataforma.

La base de la URL se configura mediante la variable de entorno `PUBLIC_APP_BASE_URL` (valor por defecto local: `http://localhost:3000`). En producción debe apuntar al frontend público, por ejemplo `https://bazaar.pib.ar`, no al bucket de imágenes ni al endpoint JSON del backend.

**Respuesta `200`:**
```json
{
  "data": {
    "productId": "b3d1a2c4-...",
    "url": "https://bazaar.example.com/products/b3d1a2c4-..."
  }
}
```

**Respuesta `404`:** si el producto no existe (`"Product not found"`), en formato `application/problem+json`.

---

#### `PATCH /products/{id}` — Actualizar producto parcialmente

Solo se modifican los campos presentes en el body. Si se incluye `stock`, el cambio se delega al inventory service.

| Campo | Tipo | Restricciones |
|-------|------|---------------|
| `title` | string | 1–150 caracteres, no vacío |
| `description` | string | 1–150 caracteres, no vacío |
| `price` | float | ≥ 0.01 |
| `stock` | int | ≥ 0 — se actualiza en el inventory service; si pasa a 0 el producto queda `out_of_stock`, si vuelve a ser > 0 desde `out_of_stock` queda `active` |
| `category` | string | 1–150 caracteres, no vacío (se normaliza a minúsculas) |
| `status` | `active` \| `inactive` \| `out_of_stock` | Los cambios manuales de status tienen precedencia sobre la sincronización automática |

**Respuesta `200`:** objeto `ProductResponse` con los datos actualizados.  
**Respuesta `404`:** error en formato `application/problem+json` si el producto no existe.

---

#### `DELETE /products/{id}` — Eliminar producto

Elimina el producto de catalog, borra sus imágenes de DigitalOcean Spaces y elimina su entrada de stock en el inventory service.

**Respuesta `204`:** sin contenido.  
**Respuesta `404`:** error en formato `application/problem+json` si el producto no existe.

---

#### `POST /products/{id}/images` — Agregar imágenes

**Body (multipart/form-data):** uno o más archivos bajo el campo `files` (JPEG, PNG o WebP, máx. 10 MB c/u).

**Respuesta `200`:** objeto `ProductResponse` con el array `images` actualizado.

---

#### `DELETE /products/{id}/images` — Eliminar imágenes

**Body JSON:**
```json
{ "urls": ["https://cdn.../imagen.jpg"] }
```
No se pueden eliminar todas las imágenes de un producto, independientemente de su status.

**Respuesta `200`:** objeto `ProductResponse` con el array `images` actualizado.  
**Respuesta `409`:** si la operación dejaría al producto sin imágenes.

---

#### `DELETE /products/{product_id}/images/{image_key}` — Eliminar imagen por key

Elimina una imagen identificada por su nombre de archivo en el bucket (el último segmento de la URL CDN, ej: `abc123.webp`).

**Respuesta `200`:** objeto `ProductResponse` con el array `images` actualizado.  
**Respuesta `404`:** si el producto no existe o el key no pertenece al producto.  
**Respuesta `409`:** si la operación dejaría al producto sin imágenes.

---

#### `DELETE /products/{product_id}/images/bulk` — Eliminar imágenes por keys (bulk)

Elimina múltiples imágenes a partir de sus storage keys en una sola operación atómica.

**Body JSON:**
```json
{ "image_keys": ["abc123.webp", "def456.jpg"] }
```
Todos los keys deben pertenecer al producto; si alguno no existe, se rechaza toda la operación.

**Respuesta `200`:** objeto `ProductResponse` con el array `images` actualizado.  
**Respuesta `404`:** si el producto no existe o alguno de los keys no pertenece al producto (el detalle lista los keys faltantes).  
**Respuesta `409`:** si la operación dejaría al producto sin imágenes.

---

#### `PATCH /products/{id}/images/order` — Reordenar imágenes

**Body JSON:**
```json
{ "urls": ["https://cdn.../b.jpg", "https://cdn.../a.jpg"] }
```
Debe contener exactamente las mismas URLs que el producto, en el nuevo orden deseado.

**Respuesta `200`:** objeto `ProductResponse` con el nuevo orden de imágenes.

---

### Endpoints internos

Estos endpoints son accesibles **únicamente dentro del cluster de Kubernetes**. El Ingress de Nginx expone el prefijo `/catalog` para la API pública y no publica las rutas `/internal`.

#### `PATCH /internal/products/{product_id}/stock-status` — Callback de disponibilidad desde inventory

Llamado por el inventory-microservice cuando el stock de un producto cambia de/a cero.

**Body JSON:**
```json
{ "has_stock": false }
```

Comportamiento según el status actual del producto:

| Status actual | `has_stock` | Resultado |
|---|---|---|
| `active` | `false` | → `out_of_stock` |
| `out_of_stock` | `true` | → `active` |
| `inactive` | cualquiera | sin cambio (tiene precedencia del vendedor) |

**Respuesta `200`:** objeto `ProductResponse` con el status actualizado.  
**Respuesta `404`:** si el producto no existe.

---

### Formato de errores

Todos los errores siguen [RFC 7807 Problem Details](https://www.rfc-editor.org/rfc/rfc7807) con `Content-Type: application/problem+json`, incluyendo los errores de autenticación (`401`):

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Product not found",
  "instance": "/products/550e8400-e29b-41d4-a716-446655440000"
}
```

Ejemplo de error de autenticación:
```json
{
  "type": "about:blank",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing X-User-ID header",
  "instance": "/products"
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
Controller      — instancia Repository, StorageService e InventoryService; convierte schemas → DTOs
    │
    ▼
Service         — lógica de negocio: stock, imágenes, estados y excepciones de dominio
    ├──▶ Repository      — consultas SQLAlchemy y persistencia de productos
    │        └──▶ PostgreSQL
    ├──▶ StorageService  — cliente S3/DigitalOcean Spaces para imágenes
    └──▶ InventoryService — cliente HTTP real del inventory microservice
```

**Regla de dependencias:** cada capa solo conoce a la inmediatamente inferior. El servicio no importa nada de `src.schemas` ni de FastAPI. Los routers no tienen lógica de negocio ni acceso a base de datos.

**DTOs (`src/dtos.py`):** dataclasses sin validación que transportan datos entre el controller y el servicio. La validación ocurre en los schemas de Pydantic antes de construir el DTO.

**Excepciones de dominio (`src/exceptions/`):** el servicio lanza `ProductNotFound` (y similares a futuro) en lugar de devolver `None`. `main.py` registra un handler global que serializa estas excepciones a `application/problem+json` según RFC 7807.

**Búsqueda (`pg_trgm`):** durante el startup se habilita la extensión `pg_trgm` y se crean índices GIN sobre `products.title` y `products.description` para soportar búsqueda fuzzy.

## Integración con inventory service

El campo `stock` no se almacena en la base de datos del catalog. En cambio, `InventoryService` (`src/services/inventory.py`) actúa como cliente del inventory microservice:

| Operación | Comportamiento |
|-----------|---------------|
| `POST /products` | Crea el producto en catalog, asigna `active` u `out_of_stock` según el stock inicial y llama a inventory para registrar ese stock |
| `GET /products` / `GET /products/{id}` | Obtiene el stock desde inventory y lo inyecta en la respuesta |
| `PATCH /products/{id}` (con `stock`) | Delega la actualización de stock a inventory y sincroniza el status visible del producto |
| `DELETE /products/{id}` | Elimina el producto de catalog y llama a inventory para eliminar su entrada de stock |

Todas las respuestas que incluyen productos se enriquecen con el stock consultado al inventory service. `InventoryService` usa `INVENTORY_SERVICE_URL` como URL base y consume las rutas internas del microservicio privado de inventory.

El frontend NO consume inventory directamente. El cliente público debe seguir usando el gateway/Ingress de catalog, por ejemplo `http://bazaar.pib.ar/catalog`.

**Variable de entorno:** `INVENTORY_SERVICE_URL` — URL base del inventory service.
