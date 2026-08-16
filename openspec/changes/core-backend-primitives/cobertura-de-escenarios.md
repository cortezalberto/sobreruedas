# Auditoría de escenarios — C-02, tarea 7.4

> **Qué es esto.** Las cinco capabilities de C-02 declaran **72 escenarios**. Este documento dice cuáles tienen test ejecutable y **cuáles no, con el motivo**. Sin él, "los tests pasan" no dice nada sobre lo que quedó afuera.
>
> Medido el **16-ago-2026** sobre 232 tests en verde.

## Resumen

| Capability | Escenarios | Con test | Sin test |
|---|---:|---:|---:|
| `platform/api-conventions` | 15 | **15** | 0 |
| `platform/domain-events` | 14 | **13** | 1 |
| `platform/tenant-isolation` | 14 | **13** | 1 |
| `platform/identity` | 13 | **11** | 2 |
| `platform/authorization` | 16 | **0** | 16 |
| **Total** | **72** | **52** | **20** |

**52 de 72.** Los 20 que faltan se agrupan en tres causas, y ninguna es "no se hizo":

| Causa | Escenarios | Se resuelve en |
|---|---:|---|
| El bloque 6 está bloqueado por `E-001` | 16 | C-02, tras la ratificación (cierre mínimo: 20-ago-2026) |
| No existe todavía un endpoint de dominio ni un esquema de entrada | 3 | **C-05** |
| No existe todavía ningún receptor de notificaciones externas | 2 | **C-29** / **C-30** |

---

## `platform/authorization` — 0 de 16

**Bloqueado por `E-001`.** El bloque 6 no se implementó y la regla dura 12 lo prohíbe expresamente: no se escribe sobre un bloqueante sin resolver. `E-001` cierra su discusión el **20-ago-2026** y todavía le faltan los pasos (c), (d) y (e) del Artículo 8.

Agravado por `R-2`: la matriz RBAC canónica no existe en ningún documento del corpus, así que aun ratificada `E-001`, los escenarios de permisos finos siguen sin tener contra qué testear. `design.md` lo trata como riesgo, no como pendiente.

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

**C-02 no se puede archivar todavía**: por los 16 de `authorization`. El change declara la capability y no la implementó.

Cuando `E-001` ratifique, el bloque 6 cierra esos 16. Los 4 restantes son de C-05 y C-29/C-30 por construcción, y quedan registrados acá para que se cubran cuando esos changes lleguen — no para que se olviden.
