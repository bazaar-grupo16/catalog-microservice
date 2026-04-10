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
│   │   ├── enums.py            # Enumeraciones compartidas (ProductStatus)
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
│   │   └── product.py          # Request/response schemas
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
│   └── secret.yaml             # ⚠️ Template — NO commitear valores reales
├── .github/workflows/
│   └── deploy.yml
├── Dockerfile                  # Imagen de producción
├── Dockerfile.test             # Imagen para correr tests
├── docker-compose.test.yml     # Levanta PostgreSQL + test runner
├── requirements.txt
└── .env.example
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

