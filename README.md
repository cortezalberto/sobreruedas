# deRuedas Gestión

SaaS vertical **multi-tenant** para agencias de vehículos del mercado argentino. Monolito modular de 16 módulos que se comunican por eventos de dominio en Redis Streams.

Compite contra Excel, cuadernos y WhatsApp — no contra CRMs enterprise. Eso condiciona cada decisión: **simplicidad antes que features, verticalidad antes que generalidad.**

---

## Estado del proyecto

**Ola 0 — fundación.** Todavía no hay lógica de negocio. El change en curso es `C-01 foundation-setup`; el índice completo de los 32 changes está en [`CHANGES.md`](CHANGES.md).

## Levantar el entorno local

```bash
cp .env.example .env      # completá los valores reales — .env nunca se versiona
docker compose up -d      # postgres, redis, opensearch, keycloak, minio, mailhog, backend, worker, frontend-web
tools/check-services.sh   # verifica que cada servicio responda
```

Arranque en frío medido: **99 s** hasta los seis servicios de infraestructura `healthy`, contra un presupuesto de 180 s.

> ⏳ `backend`, `worker` y `frontend-web` todavía no construyen: les falta `backend/pyproject.toml` (`T-005`) y `frontend-web/package.json` (`T-006`). Mientras tanto:
>
> ```bash
> docker compose up -d postgres redis opensearch keycloak minio mailhog
> ```
>
> `check-services.sh` los reporta como `PENDIENTE`, no como `FAIL`.

> 🔴 **¿Ya tenías el entorno levantado de antes del 16-ago-2026?** Hay que recrear el volumen de PostgreSQL una vez:
>
> ```bash
> docker compose down -v && docker compose up -d
> ```
>
> [`ADR-020`](docs/adr/ADR-020-rol-de-conexion-sin-bypass-de-rls.md) agregó un rol de aplicación (`mitutu`) que no puede saltear las políticas RLS — es lo que hace que el aislamiento entre agencias exista de verdad. Ese rol lo crea el init de PostgreSQL, que **solo corre al crear el volumen**.
>
> Sin recrearlo, el backend muere con `password authentication failed for user "mitutu"`, que se lee como credencial mal copiada y manda a editar el `.env`, donde no hay nada que arreglar. `check-services.sh` detecta el caso y te dice esto mismo.

**¿Un puerto ocupado?** Los mapeos del host son configurables sin tocar el compose — poné el override en tu `.env`:

```bash
POSTGRES_PORT=5442
```

Disponibles: `POSTGRES_PORT`, `REDIS_PORT`, `OPENSEARCH_PORT`, `KEYCLOAK_PORT`, `KEYCLOAK_MGMT_PORT`, `MINIO_PORT`, `MINIO_CONSOLE_PORT`, `MAILHOG_SMTP_PORT`, `MAILHOG_WEB_PORT`, `BACKEND_PORT`, `FRONTEND_PORT`.

| Servicio | Local |
|---|---|
| API (backend) | http://localhost:8000 |
| Frontend web | http://localhost:3000 |
| Keycloak | http://localhost:8080 |
| MinIO | http://localhost:9000 |
| OpenSearch | http://localhost:9200 |
| Mailhog | http://localhost:8025 |

## Cómo está organizado el repositorio

| Directorio | Qué contiene |
|---|---|
| [`backend/`](backend/) | API FastAPI, SQLAlchemy 2.x, Alembic. Los 16 módulos viven en `app/modules/` |
| [`frontend-web/`](frontend-web/) | Next.js 14+ con App Router — la aplicación del cliente |
| [`frontend-mobile/`](frontend-mobile/) | React Native + Expo. **Sin tareas asignadas todavía** — ver `ADR-018` |
| [`frontend-admin/`](frontend-admin/) | Backoffice de deRuedas, estructura espejo de `frontend-web/` |
| [`infra/`](infra/) | Soporte del entorno local, override de despliegue del VPS y configuración de observabilidad — sin Terraform ni Kubernetes ([`ADR-023`](docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md)) |
| [`tools/`](tools/) | Utilidades de desarrollo y verificación |
| [`docs/sdd/`](docs/sdd/) | **Corpus fuente inmutable**: los 11 documentos vinculantes del SDD |
| [`docs/adr/`](docs/adr/) | ADRs posteriores al SDD — las decisiones que toma el proyecto |
| [`knowledge-base/`](knowledge-base/) | Material derivado del corpus: 16 archivos temáticos navegables |
| [`openspec/`](openspec/) | Artefactos de planificación de cada change |

## Por dónde empezar a leer

**No arranques por el código.** Todavía casi no hay.

1. [`CLAUDE.md`](CLAUDE.md) — stack, reglas duras y flujo de trabajo. Es el punto de entrada.
2. [`knowledge-base/`](knowledge-base/) — el corpus destilado en 16 archivos temáticos.
3. ⚠️ [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) — **leelo antes de escribir una línea.** 54 inconsistencias documentadas entre los documentos fuente. Al 13-ago-2026 quedan **9 bloqueantes abiertos**.
4. [`docs/adr/`](docs/adr/) — por qué el proyecto decidió lo que decidió.
5. [`CHANGES.md`](CHANGES.md) — en qué orden se construye.

### Precedencia entre documentos

Cuando dos documentos se contradicen, manda [`ADR-000`](docs/adr/ADR-000-precedencia-documental.md): jerarquía por autoridad con competencia por dominio. La constitución (`N0`) gana siempre; los planes de seguridad, testing y SRE (`N3`) prevalecen sobre la spec técnica **dentro de su dominio propio**, nunca sobre la constitución.

**La recencia no desempata.** Los 11 documentos se generaron en una sola sesión de 8 h 41 min: sus fechas ordenan por generación, no por deliberación.

## Reglas que no se negocian

Derivan de `docs/sdd/deRuedas-constitucion.md`. La lista completa, con sus anclas, está en [`CLAUDE.md`](CLAUDE.md).

1. **Ninguna query sin contexto de tenant.** Tres capas simultáneas: `SET LOCAL app.current_tenant`, política RLS y `tenant_id` en la query. `tenant_id` se deriva del token, nunca del body.
2. **Las contraseñas no se tocan.** La autenticación se delega enteramente a Keycloak ([`ADR-026`](docs/adr/ADR-026-autenticacion-delegada-sin-password-hash.md)). Si aparece `password_hash`, `mfa_secret` o `verify_password`, está mal — un test recorre el AST y lo frena.
3. **Nunca borrado físico.** Soft delete universal.
4. **Nunca secretos en el repositorio.** Solo `.env.example` con valores ficticios.
5. **Cobertura: 80 % de líneas y 60 % de ramas**, backend, global — y no decrece entre commits ([`ADR-014`](docs/adr/ADR-014-umbrales-de-cobertura.md)).
6. **Nunca mocks de base de datos.** Los tests de integración usan PostgreSQL, Redis y MinIO reales vía testcontainers.

## Verificaciones

```bash
python tools/check-md-links.py
```

Comprueba que no haya enlaces markdown rotos en el repositorio. Sale con código 1 si encuentra alguno.

---

*El cuerpo documental de este proyecto es corpus fuente inmutable. Las decisiones nuevas se registran como ADR en [`docs/adr/`](docs/adr/), nunca editando `docs/sdd/`.*
