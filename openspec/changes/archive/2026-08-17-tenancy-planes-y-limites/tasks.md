# C-04 · Tareas

> **Gobernanza CRÍTICA.** `tenants` es la entidad raíz que toda otra tabla referencia por `tenant_id`, y `plans`/`subscriptions` son datos de facturación. El usuario aprobó explícitamente escribir el change completo el 17-ago-2026, tras resolver `IN-03` e `IN-04`.

> **TDD estricto.** Cada tarea de implementación va precedida de su test. El orden dentro de cada bloque no es decorativo.

## 1. Bloqueantes — se resuelven antes de escribir código

- [x] 1.1 `IN-03` (límites por plan): registrar la decisión de Dirección en `design.md` `D-2` con la tabla de límites definitiva
- [x] 1.2 `IN-04` (moneda): registrar en `design.md` `D-3` la conservación de `price_ars` **y** la consecuencia de que los precios no puedan salir del mismo documento que los límites
- [x] 1.3 Verificar que ninguna de las dos decisiones contradice a N0 — ninguna lo hace: la constitución no fija precios ni cuotas

## 2. Validador de CUIT — `core/validadores_ar.py`

- [x] 2.1 Test: un CUIT válido con guiones se acepta y se normaliza a la forma canónica
- [x] 2.2 Test: el mismo número sin guiones se acepta y normaliza al mismo valor
- [x] 2.3 Test: dígito verificador incorrecto se rechaza
- [x] 2.4 Test: prefijo fuera de las categorías de AFIP (`20 23 24 27 30 33 34`) se rechaza aunque el dígito sea correcto
- [x] 2.5 Test: longitud, caracteres no numéricos y cadena vacía se rechazan
- [x] 2.6 Implementar el validador módulo 11 con la serie `5 4 3 2 7 6 5 4 3 2`
- [x] 2.7 Test del resto 10 y del resto 11 — los dos casos de borde del algoritmo, que son donde toda implementación de CUIT se equivoca

## 3. Migraciones

- [x] 3.1 Test: la extensión PostGIS queda instalada tras migrar
- [x] 3.2 `004` — `CREATE EXTENSION postgis` (`D-4`)
- [x] 3.3 `005` — `plans` con `max_whatsapp_messages_month` (`D-2`) y seed idempotente que **no pisa** lo existente
- [x] 3.4 Test: el seed deja los tres planes con los límites de `D-2` y los precios de `D-3`
- [x] 3.5 Test: correr el seed dos veces no duplica ni sobrescribe un precio modificado a mano
- [x] 3.6 `006` — `tenant_status_enum` + `tenants`, con `plan_id` nullable (`D-8`)
- [x] 3.7 `007` — `branches` con `deleted_at` (`D-5`), RLS, `FORCE` y política
- [x] 3.8 `008` — `subscription_status_enum` + `subscriptions`, RLS, `FORCE` y política
- [x] 3.9 Verificar que el lint de DDL destructivo de la regla dura 13 pasa sin necesitar el marcador `# migracion-contract:` — las cinco son aditivas
- [x] 3.10 Verificar que el detector introspectivo de `pg_policies` **exige** política sobre `branches` y `subscriptions` y no se queja de `tenants` ni `plans` (`D-1`)

## 4. Modelos y schemas — `modules/tenancy/`

- [x] 4.1 `models.py`: `Plan`, `Tenant`, `Branch`, `Subscription` sobre la `Base` declarativa de C-02
- [x] 4.2 Test de arquitectura: todo modelo con `tenant_id` hereda de `Base` y tiene su política — reutiliza el test introspectivo existente
- [x] 4.3 `schemas.py`: entrada y salida Pydantic v2. **`tenant_id` excluido de todo schema de entrada** (regla dura 1)
- [x] 4.4 Test: un schema de entrada que reciba `tenant_id` en el body **lo rechaza** — se cambió de *ignorar* a `extra="forbid"`, ver `D-10`
- [x] 4.5 Test: el CUIT se valida en el schema, no solo en la base

## 5. Repositorio y servicio

- [x] 5.1 Test: crear una agencia con CUIT duplicado —en cualquiera de sus dos formas— se rechaza
- [x] 5.2 Test: crear una agencia con `slug` duplicado se rechaza
- [x] 5.3 Test: una agencia dada de baja no aparece en el listado ordinario
- [x] 5.4 Test: el CUIT de una agencia dada de baja **sigue ocupado**
- [x] 5.5 Implementar `repository.py` con el filtro de soft delete por defecto
- [x] 5.6 Implementar `service.py`: alta, baja, cambio de estado, alta y baja de sucursal
- [x] 5.7 Test: una agencia recién creada queda con zona horaria e idioma argentinos por defecto
- [x] 5.8 Test de aislamiento: dos agencias con sucursales, consulta en contexto de una devuelve solo las suyas
- [x] 5.9 Test de aislamiento: consulta de sucursales sin contexto devuelve cero filas
- [x] 5.10 Test de aislamiento: crear una sucursal atribuida a otra agencia se rechaza

## 6. `PlanLimitsService` — `modules/tenancy/limits.py`

- [x] 6.1 Test: alta que llega justo al límite se permite
- [x] 6.2 Test: alta que supera el límite se rechaza y **no** crea la fila
- [x] 6.3 Test: `0 = ilimitado` **no** se lee como cero permitidos (`D-2`) — el caso que falla en silencio
- [x] 6.4 Test: un registro dado de baja libera su lugar
- [x] 6.5 Test: un usuario desactivado **sigue** ocupando su lugar (`D-7`)
- [x] 6.6 Test: el límite de una agencia no lo afecta otra con el mismo plan
- [x] 6.7 Implementar `assert_can_add_user`, `assert_can_add_vehicle`, `assert_can_add_branch` contando contra la base (`D-7`)
- [x] 6.8 Agregar `PlanQuotaExceeded` a `core/errors.py` con estado **402** (`D-6`)
- [x] 6.9 Test: el rechazo por cuota se distingue del rechazo por permisos y del de autenticación
- [x] 6.10 Test: el cuerpo RFC 7807 identifica el recurso agotado y el techo, con código estable
- [x] 6.11 Documentar en el docstring de `assert_can_add_vehicle` la condición de carrera asumida y su arreglo identificado (`D-7`)

## 7. Cierre

- [x] 7.1 Suite completa verde, cobertura ≥ 80 % líneas y **sin decrecer**
- [x] 7.2 `ruff`, `black` y `mypy --strict app` en 0
- [x] 7.3 `openspec validate --changes --specs --strict` verde
- [x] 7.4 Auditar los escenarios de las dos capabilities contra los tests que existen de verdad, y escribir la tabla — la lección de C-01: el conteo honesto vive acá, no en `CHANGES.md`
- [x] 7.5 Actualizar el estado de C-04 en `CHANGES.md`


---

## Tarea 7.4 — Auditoría de escenarios: **22 de 22**

Cruzados los escenarios de las dos delta specs contra los tests que existen de verdad, no contra los que deberían existir. La lección de C-01 es que este número vive acá.

| Capability | Escenarios | Con test ejecutable | Estado |
|---|---|---|---|
| `tenancy/organization` | 10 | **10** | ✅ completa |
| `tenancy/plan-limits` | 12 | **12** | ✅ completa |

**133 tests** repartidos así:

| Archivo | Tests | Qué cubre |
|---|---|---|
| `tests/unit/test_validadores_ar.py` | 51 | identidad fiscal: dígito, prefijo, formas de escritura |
| `tests/unit/test_tenancy_schemas.py` | 27 | contrato de entrada, `tenant_id` prohibido en el body |
| `tests/integration/test_tenancy_service.py` | 34 | alta, duplicados, baja, ciclo de estados, **los 3 de aislamiento** |
| `tests/integration/test_plan_limits.py` | 21 | catálogo, cuotas, sin techo, falla cerrado |

### Los tres de aislamiento no son vacíos, y se comprobó

Un test de aislamiento que corre sobre una tabla vacía da verde sin probar nada. Se verificó contra la base:

```
con contexto de tenant ve:  1 sucursal
sin contexto ve:            0
total real en la tabla:     7
```

Hay siete filas y la sesión sin contexto ve cero: la política está actuando, no falta data. Y el test de escritura cross-tenant exige `InsufficientPrivilegeError` —que es como PostgreSQL reporta el rechazo de una política RLS— en vez de `pytest.raises(Exception)`, que pasaría igual con una FK rota o un typo.

### Dos cosas que encontró la cobertura, no una revisión

- **`Plan.sin_techo()` no lo llamaba nadie.** `limits.py` compara contra la constante directamente. Se **borró** en vez de escribirle un test: un test para código muerto deja el código muerto y además lo protege.
- **`test_una_fk_rota_no_sale_como_duplicado` no ejercitaba lo que decía.** Hacía `sesion.flush()` directo, sin pasar por `_grabar()`, así que afirmaba algo cierto sin recorrer el camino que auditaba. Reescrito para entrar por `crear_sucursal`.

### Estado final del change — **51 de 51**

| | |
|---|---|
| Suite completa | **413 tests verdes** |
| Cobertura global | **97.56 %** — subió desde 97.00 %, no decreció (regla dura 5) |
| Los 5 módulos de `tenancy` | **100 % de líneas y ramas** |
| `ruff` · `black` · `mypy --strict app` | 0 |
| `openspec validate --changes --specs --strict` | verde |
