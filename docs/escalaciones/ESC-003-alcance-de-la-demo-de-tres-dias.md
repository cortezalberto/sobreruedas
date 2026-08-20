# ESC-003 — El MVP no entra en tres días, y qué se entrega en su lugar

- **Estado**: ✅ **CERRADA** el 2026-08-20 — **opción B: una rebanada vertical completa, con el resto diferido y escrito**
  > **Qué se decidió**: se entrega **login + gestión de stock, de punta a punta y multi-tenant real**. Todo lo demás queda **diferido, no cancelado**: sigue en `CHANGES.md` con su alcance, sus dependencias y su lugar en el grafo.
  >
  > **Por qué esta y no las otras dos**: repartir tres días entre los 32 changes deja 32 cosas a medias y ninguna demostrable (opción A). Recortar la calidad para abarcar más (opción C) es lo que produjo hoy el hallazgo de las catorce rutas abiertas — y ese hallazgo salió de un gate que tarda segundos.
  >
  > **Consecuencia asumida, y es la que importa**: el producto que sale **no publica en el portal deRuedas**. Eso no es una funcionalidad menos: es la razón de ser de la épica E3 y el mecanismo del *lock-in* que `01_vision_y_objetivos.md` usa para justificar la inversión entera. Lo que se entrega demuestra el producto; **no demuestra la tesis de negocio**.
- **Fecha**: 2026-08-20
- **Eleva**: Tech Lead
- **Decide**: **Dirección** — es una decisión de alcance de producto, no técnica
  > ⚠️ Igual que en `ESC-001` y `ESC-002`, hoy Dirección y Tech Lead son la misma persona. No vacía la escalación: le cambia el sombrero. Elegir qué **no** se construye con un plazo encima es una decisión de producto, y queda fechada acá en vez de resolverse sola por lo que se alcanzó a hacer.
- **Origen**: instrucción de Dirección del 20-ago-2026 — *"necesito terminar todo el proyecto en 3 días"*
- **Afecta**: `C-09`, `C-10`, `C-18`, `C-22`, `C-23`, `C-29`…`C-32`, y el bloque 9 de `foundation-setup`
- **Relacionada con**: `R-1` / `PA-25` — el contrato de la API del portal

---

## El número, sin vueltas

El proyecto son **32 changes y 194 tareas**. Al 20-ago-2026 hay **dos changes cerrados**: `foundation-setup` (parcial, 81/95) y `core-backend-primitives` (57/57, archivado hoy).

Tres días no alcanzan para los treinta restantes. Eso no es una estimación conservadora ni una postura: es la diferencia entre lo hecho en varias semanas y lo que queda.

La pregunta útil no es *"¿entra?"* sino *"¿qué es lo máximo demostrable en tres días?"*. Esta escalación responde esa.

## Lo que se entrega

**Una rebanada vertical: una agencia entra al sistema, ve su stock, carga un vehículo, le cambia el estado e importa una planilla.** Con aislamiento multi-tenant real y la matriz de permisos aplicándose.

Se elige stock y no otra cosa porque **el backend ya está hecho y probado**: vehículos, importación CSV, RBAC, aislamiento, 739 tests. Lo que falta es poder entrar y verlo. Es el tramo más corto entre *"no se puede usar"* y *"se puede usar"*.

| Día | Qué |
|---|---|
| 1 | `C-05` recortado — tabla `users`, `GET /auth/me`, y el gate de aislamiento `T-027` |
| 2 | Login real en el frontend contra Keycloak, con el token viajando al backend |
| 3 | La pantalla de stock — listado, ficha, alta, cambio de estado |

## Lo que se difiere, y por qué cada uno

| Change | Motivo |
|---|---|
| **`C-22`, `C-23`** — portal deRuedas | Depende de **otro equipo**. `R-1` está abierto desde el inicio del proyecto y ningún documento del corpus especifica esa API. Meterlo en tres días es garantizar el bloqueo. |
| **`C-29`…`C-32`** — WhatsApp | Cuatro changes, API de Meta, y un proceso de aprobación con tiempos que no controlamos. |
| **`C-18`** — OpenSearch | PostgreSQL alcanza de sobra para el volumen de una demostración. Es optimización de un problema que todavía no existe. |
| **`C-09`, `C-10`** — backoffice y onboarding | Sirven para **operar** el producto, no para demostrarlo. Con `make seed` la agencia ya existe. |
| **Bloque 9 de `foundation-setup`** (14 tareas) | Provisioning de un VPS real: firewall, TLS, claves `age`, archivado de WAL fuera del servidor, ejercicio de restauración fechado. Se come un día entero de los tres y **no cambia lo que se puede mostrar**. Queda en Docker Compose. |

**Diferido no es cancelado.** Ninguno se saca de `CHANGES.md`, ninguno pierde su alcance ni su lugar en el grafo de dependencias. La cobertura sigue siendo 194/194.

## Lo que NO se recorta, y por qué está escrito acá

Dos gates siguen siendo bloqueantes aunque haya plazo:

- **El recorrido de rutas sin declaración de acceso.** Hoy encontró **catorce endpoints abiertos**: cualquier usuario autenticado podía archivar el vehículo de cualquier agencia. Corre en segundos y detecta lo que una revisión a ojo no ve, porque el defecto es una línea que **falta**.
- **Los tests de aislamiento multi-tenant.** Es lo único que impide que una agencia vea el stock de otra. En un SaaS vertical eso no es un defecto: es el final del producto.

Juntos tardan menos de dos minutos. Apagarlos no da velocidad; cambia un riesgo conocido por uno invisible.

Lo que **sí** se relaja: TDD estricto en el frontend (se prueban las costuras, no cada componente), la ceremonia de ADR salvo que se contradiga el corpus, el objetivo de cobertura en código nuevo de interfaz, y el ciclo `propose`/`archive` de OpenSpec — se trabaja directo sobre las tareas.

## Alternativas consideradas

**A — Repartir los tres días entre los 32 changes.** Descartada: produce treinta y dos cosas a medias y ninguna que se pueda mostrar. Y una rebanada horizontal no se puede probar de punta a punta, así que tampoco se sabe si funciona.

**C — Recortar la calidad para abarcar más alcance.** Descartada por evidencia del mismo día: las catorce rutas abiertas las encontró un gate automático, no una revisión. El primer control que se apaga por apuro es justo el que después nadie vuelve a prender.

## Lo que esta escalación NO cierra

- **`R-1` sigue abierto.** Esto no lo resuelve: lo saca del camino de los tres días. La acción que sí lo mueve —pedirle al equipo del portal un sandbox y un par petición/respuesta reales— corre **en paralelo** y no depende del desarrollo.
- **La fecha de los diferidos.** No se fija acá. Depende de cuándo llegue el contrato del portal y de qué se decida después de ver la demostración.
- **La tesis de negocio.** Que el producto salga sin publicación automática es lo que hay que mirar al evaluar la demostración: prueba que el sistema funciona, no que las agencias vayan a retener la suscripción.
