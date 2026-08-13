# Tareas — `foundation-setup` (C-01)

> **Governance: ALTO.** Se propone y se espera revisión humana antes de escribir código.
> Cobertura de tests aplicable desde el primer commit: **80 % líneas / 60 % ramas** (ver `design.md` D-3).
> Mapeo a las tareas del plan: `T-001` … `T-008`.

## 1. Reubicación documental y siembra de ADRs

Precede a todo lo demás: el §4.1 no se puede materializar mientras `docs/` esté ocupado por el corpus fuente.

- [ ] 1.1 Mover los 11 documentos de `docs/*.md` a `docs/sdd/` con `git mv` (preserva historial)
- [ ] 1.2 Mover todo el contenido de `decisions/` a `docs/adr/` con `git mv` (`ADR-000`, `ADR-015`, `ADR-016`, `ADR-017` y la enmienda `E-001`) y eliminar el directorio vacío
- [ ] 1.3 Actualizar los enlaces a `docs/` en los 16 archivos de `knowledge-base/`
- [ ] 1.4 Actualizar los enlaces a `docs/` y a `decisions/` en `CLAUDE.md`, `AGENTS.md` y `CHANGES.md`
- [ ] 1.5 Corregir en `CHANGES.md` la referencia a `frontend/`, que en el §4.1 es `frontend-web/`
- [ ] 1.6 Verificar automáticamente que no queda ningún enlace markdown roto en el repositorio
- [ ] 1.7 Escribir `docs/adr/ADR-013-variables-de-entorno.md` con la tabla canónica de `design.md` D-2 (cierra `R-3` / `PA-06`)
- [ ] 1.8 Escribir `docs/adr/ADR-014-umbrales-de-cobertura.md` registrando 80 % líneas / 60 % ramas y la enmienda al plan de testing (cierra `IN-22`)
- [ ] 1.9 Corregir en `docs/sdd/deRuedas-plan-implementacion.md` las anclas divergentes de `ADR-002`, `ADR-005` y `ADR-011` según `design.md` D-4 (cierra `IN-29`)
- [ ] 1.10 Corregir `ENVIRONMENT` → `APP_ENV` en la tabla de `knowledge-base/08_arquitectura_propuesta.md`

## 2. Estructura del monorepo — `T-001`

- [ ] 2.1 Crear el árbol completo del §4.1 con `.gitkeep` en los directorios vacíos
- [ ] 2.2 Escribir el `README.md` raíz: descripción, enlaces al cuerpo SDD y cómo levantar el entorno
- [ ] 2.3 Extender el `.gitignore` para Python (`__pycache__`, `.venv`, `.pytest_cache`), Node (`node_modules`, `.next`), entornos (`.env`, `.env.local`) e IDEs
- [ ] 2.4 Escribir `.env.example` con las ~34 variables de `ADR-013`, valores ficticios y comentarios — sin un solo valor real
- [ ] 2.5 Verificar el árbol con `tree -L 3` contra el §4.1, entrada por entrada

## 3. Entorno local — `T-002`

- [ ] 3.1 Escribir `docker-compose.yml` con `postgres`, `redis`, `opensearch`, `keycloak`, `minio`, `mailhog`, `backend`, `worker` y `frontend-web`
- [ ] 3.2 Configurar el init de PostgreSQL 16 habilitando `pgcrypto`, `pg_trgm`, `postgis` y `uuid-ossp`
- [ ] 3.3 Versionar el archivo de importación del realm `deruedas-dev` de Keycloak
- [ ] 3.4 Configurar la creación automática del bucket `deruedas-media` en MinIO al arrancar
- [ ] 3.5 Definir volúmenes nombrados (`pg_data`, `redis_data`, `minio_data`) y las redes `default` y `observability`
- [ ] 3.6 Escribir `backend/Dockerfile` y `frontend-web/Dockerfile` con hot-reload por volume mount
- [ ] 3.7 Escribir `docker-compose.test.yml` con servicios efímeros, sin volúmenes persistentes
- [ ] 3.8 Escribir `tools/check-services.sh` que pingea cada servicio y reporta OK/FAIL
- [ ] 3.9 Verificar que `docker compose up -d` deja todos los servicios `healthy` en menos de tres minutos

## 4. Contrato de configuración — `T-004`

Cubre la capability `platform/configuration`. Los tests van primero.

- [ ] 4.1 Escribir los tests de validación de tipos y defaults de `Settings`
- [ ] 4.2 Escribir los tests de fallo temprano: variable obligatoria ausente y valor con tipo inválido, verificando que el error **nombra la variable**
- [ ] 4.3 Escribir los tests de enmascarado de secretos en serialización, `repr` y mensajes de error
- [ ] 4.4 Escribir el test de rechazo de `APP_ENV` fuera de `local | ci | staging | production`
- [ ] 4.5 Implementar `backend/app/config.py` con Pydantic Settings v2 y los grupos de `design.md` D-2
- [ ] 4.6 Implementar la validación al arranque con muerte temprana y mensaje que nombra la variable
- [ ] 4.7 Implementar el enmascarado de campos sensibles y el singleton `get_settings()` cacheado
- [ ] 4.8 Verificar que `.env.example` y los grupos de `Settings` cubren exactamente el mismo conjunto de variables

## 5. Bootstrap del backend — `T-005`

Cubre la capability `platform/service-health`. Los tests van primero.

- [ ] 5.1 Escribir los tests de la sonda de vida: respuesta exitosa, presencia de versión y marca temporal, acceso sin credenciales
- [ ] 5.2 Escribir los tests de la sonda de disponibilidad en condiciones normales y degradadas, incluida la recuperación sin reinicio
- [ ] 5.3 Escribir los tests de correlación de peticiones: identificador generado y provisto por el cliente
- [ ] 5.4 Escribir el test de que la documentación interactiva no se sirve con `APP_ENV=production`
- [ ] 5.5 Implementar `backend/app/main.py`: aplicación, middleware de CORS y GZip, lifespan asíncrono
- [ ] 5.6 Implementar el middleware de identificador de correlación
- [ ] 5.7 Implementar las sondas de vida y disponibilidad
- [ ] 5.8 Implementar los handlers de excepción globales y el gate de documentación por ambiente
- [ ] 5.9 Verificar que el servicio arranca y que detener Redis alterna la sonda de disponibilidad y la restablece

## 6. Alembic — `T-007`

- [ ] 6.1 Escribir `backend/alembic.ini` con `script_location`, `file_template` (`NNN_descripcion.py`) y timezone
- [ ] 6.2 Escribir `alembic/env.py` leyendo la Base declarativa y la configuración desde `Settings`
- [ ] 6.3 Crear la migración baseline `000_baseline.py` vacía
- [ ] 6.4 Agregar los objetivos `make migrate` y `make migrate-down-one`
- [ ] 6.5 Verificar `upgrade head` sobre base limpia y `downgrade base` en sentido inverso

## 7. Bootstrap del frontend web — `T-006`

- [ ] 7.1 Inicializar `frontend-web/` con Next.js 14+ y App Router
- [ ] 7.2 Configurar TypeScript con `strict`, `noImplicitAny` y `noUncheckedIndexedAccess`
- [ ] 7.3 Configurar Tailwind con la paleta por defecto y el punto de extensión marcado `TODO(C-07)`
- [ ] 7.4 Configurar los alias de rutas `@/components`, `@/lib` y `@/hooks`
- [ ] 7.5 Configurar ESLint con `next/core-web-vitals` más `jsx-a11y`, y Prettier compartido
- [ ] 7.6 Escribir el layout raíz con metadatos y la página home placeholder
- [ ] 7.7 Verificar `npm run dev`, `npm run build` y `tsc --noEmit` sin errores

## 8. Pipeline de integración — `T-003`

Cubre la capability `platform/delivery-pipeline`.

- [ ] 8.1 Escribir `.github/workflows/ci.yml` con los seis jobs de `design.md` D-6
- [ ] 8.2 Configurar el gate de cobertura al **80 % de líneas y 60 % de ramas**, con fallo bloqueante
- [ ] 8.3 Configurar las exclusiones de cobertura para archivos de scaffolding sin lógica, de forma explícita y auditable
- [ ] 8.4 Configurar la comprobación de que la cobertura no decrece respecto de `main`
- [ ] 8.5 Configurar el job de seguridad: `pip-audit`, `npm audit` y `gitleaks`, bloqueante en alta o crítica y ante cualquier secreto
- [ ] 8.6 Configurar el job de integración levantando `docker-compose.test.yml`
- [ ] 8.7 Configurar la caché de dependencias de `pip` y `npm`
- [ ] 8.8 Verificar con una propuesta de cambio de prueba: pasa en verde en menos de 15 minutos
- [ ] 8.9 Verificar que un test que falla y una cobertura insuficiente bloquean efectivamente la integración

## 9. Despliegue a staging — `T-008` · Kubernetes + ArgoCD

> **Desbloqueado.** `IN-16` cerrado por `ADR-015` el 13-ago-2026: Kubernetes con GitOps vía ArgoCD.
> Frontera de seguridad no negociable: **GitHub Actions no recibe credenciales del cluster.** Su permiso máximo es escribir un tag de imagen en el repositorio de manifests.

**Infraestructura (Terraform)**

- [ ] 9.1 Escribir `infra/terraform/staging/` provisionando el cluster de Kubernetes con disponibilidad multi-zona
- [ ] 9.2 Provisionar con Terraform la red, la base gestionada, los buckets, el registry, el DNS y los certificados
- [ ] 9.3 Instalar ArgoCD en el cluster y configurar su acceso de solo lectura al repositorio de manifests

**Cargas de trabajo (manifests)**

- [ ] 9.4 Escribir en `infra/k8s/` los manifests de `backend`, `worker` y `frontend-web`: `Deployment`, `Service`, `Ingress` y `ConfigMap`
- [ ] 9.5 Configurar los `Secret` desde el gestor de secretos del proveedor — **nunca en el repositorio** (regla dura 4)
- [ ] 9.6 Configurar las sondas `readinessProbe` y `livenessProbe` de Kubernetes apuntando a `/ready` y `/health`
- [ ] 9.7 Configurar la mecánica azul-verde: dos `ReplicaSet` y un `Service` cuyo selector determina el pool activo

**Pipeline (GitHub Actions)**

- [ ] 9.8 Escribir `.github/workflows/deploy-staging.yml` disparado por push a `main` tras CI en verde
- [ ] 9.9 Configurar el build, la firma y el push de imágenes etiquetadas con el SHA del commit
- [ ] 9.10 Configurar la actualización del tag en el repositorio de manifests — el pipeline **termina acá**
- [ ] 9.11 Verificar que el pipeline no tiene ni necesita `kubeconfig` ni credenciales del cluster en sus secretos

**Verificación y reversión**

- [ ] 9.12 Configurar las pruebas de humo contra el pool nuevo **antes** de conmutar el selector, durante cinco minutos
- [ ] 9.13 Verificar que un fallo en las pruebas de humo deja el selector sin mover y el pool anterior sirviendo
- [ ] 9.14 Configurar la notificación al equipo ante un despliegue fallido
- [ ] 9.15 Verificar que ArgoCD detecta y reporta la deriva ante un cambio manual en el cluster
- [ ] 9.16 Verificar el despliegue automático extremo a extremo y la reversión por `git revert` de los manifests

## 10. Verificación de cierre

- [ ] 10.1 Verificar que el pipeline corre verde de punta a punta sobre el repositorio completo
- [ ] 10.2 Verificar que ningún valor sensible real quedó versionado (`gitleaks` sobre todo el historial del change)
- [ ] 10.3 Verificar que las tres capabilities tienen sus escenarios cubiertos por tests ejecutables
- [ ] 10.4 Verificar que `IN-22`, `IN-29` y `R-3` quedaron cerrados con su ADR correspondiente
- [ ] 10.5 Actualizar el estado de C-01 en `CHANGES.md`
