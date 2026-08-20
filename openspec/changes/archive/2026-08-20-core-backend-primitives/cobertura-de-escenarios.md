# Auditoría de escenarios — C-02, tarea 7.4

> **Qué es esto.** Las cinco capabilities de C-02 declaran **77 escenarios**. Este documento dice cuáles tienen test ejecutable y **cuáles no, con el motivo**. Sin él, "los tests pasan" no dice nada sobre lo que quedó afuera.
>
> Medido el **16-ago-2026** sobre 232 tests en verde. **Actualizado el 17-ago-2026**: `platform/authorization` pasó de 16 a **21 escenarios** por [`ADR-024`](../../../docs/adr/ADR-024-matriz-rbac-canonica.md).
>
> **Actualizado el 20-ago-2026** — bloque 6 implementado, sobre **739 tests en verde**. `platform/authorization` pasó de 21 a **25 escenarios** ([`ADR-033`](../../../docs/adr/ADR-033-alcance-self-distinto-de-own.md) agregó el alcance propio; [`ADR-034`](../../../docs/adr/ADR-034-transiciones-como-tercer-eje-del-permiso.md) agregó el requisito de transiciones, con 3 escenarios) y de **0 a 22 con test**.

## Resumen

| Capability | Escenarios | Con test | Sin test |
|---|---:|---:|---:|
| `platform/api-conventions` | 15 | **15** | 0 |
| `platform/domain-events` | 14 | **13** | 1 |
| `platform/tenant-isolation` | 14 | **13** | 1 |
| `platform/identity` | 13 | **11** | 2 |
| `platform/authorization` | 25 | **22** | 3 |
| **Total** | **81** | **74** | **7** |

**74 de 81.** Los 7 que faltan se agrupan en dos causas, y ninguna es "no se hizo":

| Causa | Escenarios | Se resuelve en |
|---|---:|---|
| No existe todavía el endpoint ni el esquema de entrada que el escenario necesita | 3 | **C-05** |
| No existe todavía la superficie sobre la que ejercer el mecanismo | 2 | **C-14** (campos en escritura) · **C-19** (espacio `/admin`) |
| No existe todavía ningún receptor de notificaciones externas | 2 | **C-29** / **C-30** |

> El desglose por causa de la medición anterior sumaba 26 contra 25 de la tabla de arriba. Estaba mal por uno y se corrige acá; el total por capability siempre fue el bueno.

El bloqueo de `E-001` **desapareció**: la enmienda se ratificó el 20-ago-2026 y el bloque 6 quedó implementado el mismo día.

---

## `platform/authorization` — 22 de 25

✅ **Implementado el 20-ago-2026.** `E-001` se ratificó, el bloque 6 se escribió entero (`core/rbac.py`, 100 % líneas y ramas) y los 21 escenarios que estaban en 0 pasaron a tener test. La capability creció a 25 por dos ADRs que aparecieron **al transcribir la matriz**, no antes:

| ADR | Qué agregó | Escenarios |
|---|---|---:|
| [`ADR-033`](../../../docs/adr/ADR-033-alcance-self-distinto-de-own.md) | `ADR-024` usaba `own` con dos sentidos: `assigned_user_id` (§4, *"y nada más"*) y "sobre sí mismo" en Auth y Usuarios, que no tienen esa columna. Tercer valor de alcance, `self`. | +1 |
| [`ADR-034`](../../../docs/adr/ADR-034-transiciones-como-tercer-eje-del-permiso.md) | La celda *"`own`, solo `available`→`reserved`"* no cabía en dos ejes. Cerró una concesión **que estaba corriendo**: el vendedor vendía en dos saltos legales. | +3 |

### Los 3 sin test, con el motivo

| Escenario | Por qué no | Se resuelve en |
|---|---|---|
| **Modificación acotada a ciertos campos** | La celda es `vehicles:update` con `[internal_notes, assigned_user_id]`, y **`PATCH /vehicles/{id}` no tiene endpoint**. El mecanismo (`recortar`) tiene test unitario; lo que falta es la puerta por donde ejercerlo. | **C-14** |
| **Alcance acotado al propio sujeto** | Igual: `self` solo aparece en `auth:*` y `users:update`, y ni `/auth/me` ni `/users` existen. `verificar_alcance` con `Alcance.SELF` tiene test unitario en los dos sentidos. | **C-05** |
| **Rol de plataforma en el espacio administrativo** | `/admin/api/v1` **no tiene una sola ruta montada**. Se ejercita sobre un endpoint de prueba, no sobre la superficie real. | **C-19** |

⚠️ Los tres comparten forma: **el mecanismo está probado, la superficie no existe**. Es distinto de "no se probó", y hay que leerlo distinto — pero tampoco es lo mismo que verde.

### Uno que se cubrió por ausencia, y conviene saberlo

**Campo excluido pedido explícitamente** pide que el valor *"no se revele por ningún medio"*. Recortar la respuesta no alcanza: un filtro por rango sobre un campo invisible lo revela por búsqueda binaria sin mostrarlo nunca.

Hoy no hay por dónde —el orden del listado es fijo, no hay parámetro de ordenamiento ni de proyección, y ningún filtro toca `acquisition_cost_ars`—. Los dos tests que lo cubren **vigilan esa ausencia**: fallan si alguien agrega un `cost_from` o un `sort_by` de texto libre. Es lo único que la sostiene.

## `platform/identity` — 11 de 13

| Escenario | Motivo |
|---|---|
| **Receptor de notificaciones externas** | No existe ningún webhook. El primero es el de WhatsApp, en **C-29**. La lista `RUTAS_EXENTAS` está preparada para recibirlo y hay un test que falla si alguien la agranda sin más. |
| **Notificación externa con firma inválida** | Ídem. La verificación HMAC es de C-29. |

## `platform/tenant-isolation` — 13 de 14

| Escenario | Motivo |
|---|---|
| **El cuerpo intenta declarar otro tenant** | Necesita un esquema Pydantic de entrada y un endpoint que lo reciba. El primero llega con **C-05**. |

> El escenario **"El tenant viaja en el token"** se cuenta como cubierto por `test_auth_rutas.py::test_con_un_token_valido_la_peticion_se_atiende`, que verifica que el tenant se deriva del token y llega al endpoint. Que además abra la sesión bajo ese contexto no se puede probar sin un endpoint de datos — llega con C-05.

## `platform/domain-events` — 13 de 14

| Escenario | Motivo |
|---|---|
| **El consumidor falla** (y no afecta a la petición que originó el evento) | Cubierto a medias: hay test de que publicar sin consumidores funciona y de que un consumidor que falla no traba la cola. Lo que **no** hay es una petición HTTP que publique un evento y siga andando con el consumidor roto — necesita un endpoint de dominio (**C-05**). |

## `platform/api-conventions` — 15 de 15

Completa.

---

## Los dos que estaban al alcance, y se cubrieron

Al hacer esta auditoría aparecieron dos escenarios que no dependían de ningún otro change. Se escribieron en el acto en vez de anotarse como deuda:

1. **`identity` · No hay verificación local de credenciales.** `test_arquitectura.py` recorre el AST de `app/**` y falla si aparece `password_hash`, `verify_password`, `get_password_hash`, `hash_password` o `check_password` —**incluyendo definiciones**, no solo usos— o si se importa `passlib`, `bcrypt` o `argon2`. Es el guardián de la regla dura 2, del Artículo 3 y del override `O-1`, que existe porque la plantilla de `fastapi-templates` trae justamente auth local con hash de contraseñas.

2. **`tenant-isolation` · Tabla exenta declarada.** `test_una_tabla_exenta_declarada_no_se_reporta` crea una tabla sin política, comprueba que **se reporta**, la declara exenta y comprueba que **deja de reportarse**. Es el contrapeso de `test_el_detector_detecta`: sin los dos, una lista de exenciones rota —ignorada por completo o aplicada a todo— daría verde igual.

> **Hallazgo al escribir el primero.** El detector de arquitectura solo miraba *referencias*, no *definiciones*. Para `sesion_de_plataforma` está bien —`db/session.py` la define y eso es su casa—, pero para `verify_password` es al revés: que la aplicación la **defina** ES la infracción. Con un solo criterio, uno de los dos controles quedaba ciego. Ahora `usos_de` recibe `incluir_definiciones`.

## Qué significa esto para archivar C-02

**C-02 no se puede archivar todavía**: por los 21 de `authorization`. El change declara la capability y no la implementó.

Cuando `E-001` ratifique, el bloque 6 cierra esos 21. Los 4 restantes son de C-05 y C-29/C-30 por construcción, y quedan registrados acá para que se cubran cuando esos changes lleguen — no para que se olviden.
