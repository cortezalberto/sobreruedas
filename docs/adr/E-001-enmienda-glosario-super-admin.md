# E-001 — Enmienda a la constitución

## Incorporar *"Super Admin"* al glosario canónico y ratificar la equivalencia de identificadores de rol

- **Estado**: ✅ **RATIFICADA** — 20 de agosto de 2026. La constitución pasa a **v1.1**
- **Apertura**: jueves 13 de agosto de 2026
- **Cierre mínimo de discusión**: **jueves 20 de agosto de 2026** (5 días hábiles) — cumplido
- **Proponente**: Tech Lead
- **Decidió**: **decisión unipersonal del Tech Lead**. El Artículo 8 prevé *"mayoría calificada del equipo técnico y de producto"*; ese cuerpo no existe — el proyecto lo lleva una sola persona. Se registra lo que ocurrió, no la forma prevista para un equipo que no hay (obstáculo 1, resuelto el 17-ago)
- **Desbloquea**: `C-02` (`core/rbac.py`, T-014, bloque 6), `R-2` (matriz RBAC), migración inicial de `users`
- **Registrada en**: [`deRuedas-constitucion.md`](../sdd/deRuedas-constitucion.md) §Historial de enmiendas — apéndice *append-only*, opción A del obstáculo 2
- **ADR asociado**: [`ADR-017`](ADR-017-catalogo-de-roles-y-super-admin.md), que con esto pasa a **aceptado pleno**

---

## Procedimiento — Artículo 8

| Paso | Estado |
|---|---|
| (a) Propuesta escrita identificando el artículo a modificar y la justificación | ✅ **Este documento** |
| (b) Discusión abierta del equipo, mínimo 5 días hábiles | ✅ Del 13 al 20-ago-2026, cumplida sin acortar |
| (c) Aprobación por mayoría calificada del equipo técnico y de producto | ✅ **20-ago-2026** — registrada como **decisión unipersonal del Tech Lead**, no como mayoría calificada |
| (d) Registro de la enmienda con fecha, motivo y versión | ✅ **20-ago-2026** — apéndice al final de [`deRuedas-constitucion.md`](../sdd/deRuedas-constitucion.md) |
| (e) Comunicación al equipo y a los stakeholders externos relevantes | ⬜ **Pendiente — el envío es del usuario.** Texto listo más abajo |

> **¿Requiere consulta a Dirección?** El Artículo 8 la exige *"si la enmienda afecta principios fundamentales"*. Esta enmienda **no toca ningún principio**: agrega una definición a la Parte IV (Glosario) sin modificar ninguna existente. **Resuelto el 20-ago-2026: no requiere consulta a Dirección**, conforme a lo propuesto y sin objeciones durante el período de discusión.

## Qué se propone modificar

**Parte IV — Glosario y definiciones canónicas.** Únicamente por **adición**. Ninguna definición existente se modifica ni se elimina.

### Adición 1 — Nuevo término canónico: *Super Admin*

> **Super Admin**
>
> Persona del equipo de deRuedas con atribuciones de administración de la plataforma. **No es un Usuario**: no pertenece a ningún tenant y no aparece en el padrón de usuarios de ninguna agencia. Opera exclusivamente sobre los endpoints de administración de plataforma y sus acciones quedan registradas en la auditoría con su identidad propia. La distinción es sustantiva: un Usuario existe dentro de un tenant, un Super Admin existe por encima de todos.

### Adición 2 — Nota de equivalencia en la definición de *Usuario*

La definición de **Usuario** se conserva **textualmente sin cambios**. Se le agrega debajo, como nota:

> *Nota de equivalencia.* Los identificadores de rol en código y en la base de datos son `manager` ≡ Gerente, `salesperson` ≡ Vendedor, `admin_staff` ≡ Administrativo. La interfaz de usuario emplea siempre los términos en español de este glosario.

## Justificación

### 1. El modelo actual no puede representar un actor que la propia spec técnica ya define

`spec-tecnica` §4.1.3 y §4.2.11 definen **11 endpoints bajo `/admin/api/v1`** para el Super Admin. Al mismo tiempo, `users.tenant_id` es `FK NOT NULL`.

Son dos afirmaciones incompatibles dentro del mismo documento vinculante. Es `IN-02`, y sin resolverlo `C-02` no puede escribir `core/rbac.py`, ni la migración inicial de `users`, ni los tests de autorización que `plan-testing` declara bloqueantes en CI.

### 2. La adición **preserva** el glosario en lugar de contradecirlo

Este es el punto central de la propuesta, y la razón por la que se pide una adición y no una modificación.

El planteo original de `IN-01` sugería reemplazar el catálogo de tres roles del glosario por uno de cuatro. Eso **sí** habría sido una modificación contenciosa.

Al decidir que el Super Admin vive en una tabla propia (`ADR-017`), las dos definiciones del glosario quedan intactas:

| Definición vigente | Efecto de esta enmienda |
|---|---|
| *"Un usuario pertenece exactamente a un tenant"* | **Intacta.** `users.tenant_id` sigue `NOT NULL`. |
| *"Un usuario tiene un rol (Gerente, Vendedor, Administrativo)"* | **Intacta.** Siguen siendo esos tres. |

La enmienda **no cambia qué es un Usuario**. Define un término distinto que hoy falta y que el resto del corpus ya usa sin haberlo declarado.

### 3. Cierra una divergencia entre cinco documentos

`IN-01` es una de las 14 inconsistencias bloqueantes. Con `ADR-017` más esta enmienda, el catálogo queda unívoco: **cuatro roles en el sistema, tres en `user_role_enum`**, y el cuarto en su propia tabla.

### 4. La nota de equivalencia elimina una ambigüedad, no crea una

El glosario establece que un término *"se asume con el **significado** aquí establecido"*: fija significados, no lexemas. Bajo esa lectura, `manager` con el significado de Gerente no contradice nada.

Pero esa lectura hoy es **implícita**, y el Principio 5 es terminante: *"las decisiones implícitas no son vinculantes y pueden ser cuestionadas en cualquier momento"*. Ratificar la equivalencia la vuelve vinculante y evita que la discusión se reabra en cada revisión de código.

## Impacto si se ratifica

- `user_role_enum` se crea con **tres** valores: `manager`, `salesperson`, `admin_staff`.
- Se crea la tabla `super_admins`, sin `tenant_id`, **exenta de RLS**.
- `users.tenant_id` permanece `FK NOT NULL`, sin excepciones.
- `audit_logs` referencia al actor de forma polimórfica: `(tipo_de_actor, id)`.
- Se desbloquean `C-02` y la redacción de la matriz RBAC (`R-2`).
- La constitución pasa a versión 1.1, con la enmienda acumulada al final del documento como historial, según el Artículo 8.

## Impacto si se rechaza

- `ADR-017` se revisa y hay que elegir entre las alternativas descartadas: `tenant_id` nullable (rompe el invariante de aislamiento) o Super Admin solo en Keycloak (pierde trazabilidad de auditoría).
- Los 11 endpoints de `/admin/api/v1` quedan sin rol que los autorice.
- `C-02` sigue bloqueado, y con él el camino crítico completo.

## Alternativas al texto propuesto

Se someten a discusión junto con la propuesta:

1. **Llamarlo *"Administrador de Plataforma"*** en lugar de *"Super Admin"*, por coherencia con un glosario íntegramente en español. Contra: los cinco documentos que ya lo mencionan usan "Super Admin", y renombrarlo obliga a corregir todos.
2. **Omitir la nota de equivalencia** y dejar la lectura de "significado, no lexema" como interpretación. Contra: el Principio 5 la volvería no vinculante y reabrible.
3. **Definir además *"Customer Success Manager"***, la quinta persona de `historias-usuario`. Contra: ese documento es N4, no normativo, y no hay ningún endpoint ni permiso asociado. Se propone **no** incluirlo, y tratarlo si alguna vez aparece en un documento normativo.

---

## Registro de la discusión

> Completar durante el período de discusión. Las intervenciones se acumulan acá para dejar rastro, como exige el Artículo 8 para la constitución misma.

| Fecha | Participante | Postura | Comentario |
|---|---|---|---|
| 2026-08-13 | Tech Lead | Propone | Apertura de la discusión |
| 2026-08-17 | Tech Lead | Aclara | **No hay equipo**: el proyecto lo lleva una sola persona. El paso (c) se registrará como decisión unipersonal, no como mayoría calificada. El plazo de cinco días hábiles **no se acorta** — es período de enfriamiento, y acortarlo exigiría enmendar el Artículo 8. |
| 2026-08-20 | Tech Lead | **Aprueba** | Cumplido el período de discusión del 13 al 20-ago sin objeciones ni intervenciones en contra, se **aprueba la enmienda tal como fue propuesta**, sin modificaciones al texto de las dos adiciones. Se aprueba también el punto sometido a discusión sobre la consulta a Dirección: **no se requiere**, porque la enmienda agrega al glosario sin tocar ningún principio. La aprobación se asienta como **decisión unipersonal**, con esas palabras y no como mayoría calificada — el cuerpo que el Artículo 8 prevé no existe, y una mayoría ficticia sería peor que una decisión unipersonal declarada (Principio 5). |

---

# Preparación del cierre — 20-ago-2026

> ✅ **EJECUTADO el 20-ago-2026.** Los pasos (c) y (d) están hechos; el (e) queda pendiente porque el envío es del usuario. Los artefactos de abajo se conservan **como fueron redactados el 17-ago**, sin retocar: son el registro de qué se aprobó, y reescribirlos ahora borraría el rastro de que el texto no cambió entre la propuesta y la ratificación.
>
> Preparado el 17-ago-2026 · ejecutado el 20-ago-2026.

## Dos obstáculos que hay que resolver ANTES del 20, no ese día

### ✅ Obstáculo 1 — RESUELTO el 17-ago-2026: la decisión es unipersonal

El paso (c) pide *"aprobación por **mayoría calificada** del equipo técnico y de producto"*. El registro de discusión tenía una sola entrada, la del propio proponente, y eso planteaba si el paso (c) se iba a firmar sobre una discusión que no ocurrió.

**Confirmado por el Tech Lead: hoy no hay equipo. El proyecto lo lleva una sola persona.**

Entonces el paso (c) se registra como **decisión unipersonal del Tech Lead**, con esas palabras. Es perfectamente válido: una enmienda constitucional aprobada por una persona en un proyecto de una persona no tiene ningún defecto. Lo que **no** sería válido es llamarla *"mayoría calificada"* — el Principio 5 es terminante con las decisiones implícitas, y una mayoría ficticia es peor que una decisión unipersonal declarada.

#### El plazo de cinco días hábiles se respeta igual

Podría argumentarse que discutir con uno mismo no requiere una semana. **No se acorta**, por dos razones:

1. El plazo no es solo para juntar opiniones: es un **período de enfriamiento** antes de tocar la norma más alta del proyecto. Eso conserva todo su valor con una sola persona — probablemente más, porque no hay nadie que frene un impulso.
2. Acortarlo sería modificar el Artículo 8, y eso exige su propio procedimiento de enmienda. No se puede saltar el trámite invocando el trámite.

**`E-001` cierra el jueves 20-ago, como estaba previsto.**

#### ⚠️ Esto excede a `E-001` — el Artículo 8 tiene un supuesto que no se cumple

El Artículo 8 asume un equipo técnico y de producto que pueda formar mayoría. **Ese cuerpo no existe hoy**, y no va a existir para la próxima enmienda tampoco.

No se arregla acá: cada enmienda futura va a chocar con lo mismo, y va a resolverse igual de a una, o alguien va a terminar escribiendo "mayoría calificada" sin pensarlo. Corresponde una **enmienda al propio Artículo 8** que contemple el caso de decisor único —y qué pasa cuando el equipo crece—, tramitada con su propio procedimiento. Queda registrado como trabajo pendiente, no como defecto de esta enmienda.

> ✅ **Abierta el 17-ago-2026 como [`E-002`](E-002-enmienda-articulo-8-decisor-unico.md)**, con cierre mínimo el **lunes 24-ago-2026**.
>
> Se abrió sin esperar a que `E-001` cerrara, y por una razón operativa: el plazo de cinco días hábiles del Artículo 8 **corre desde la apertura**, así que demorarla solo corría el cierre. Abrirla el 17 en vez del 20 lo adelanta tres días.
>
> **`E-002` no bloquea nada** y **no condiciona a `E-001`**: son independientes. `E-001` cierra el 20-ago con su paso (c) registrado como decisión unipersonal —que es exactamente la práctica que `E-002` propone volver explícita— y no necesita esperarla.

### ✅ Obstáculo 2 — RESUELTO el 17-ago-2026: opción A

**Decidido por el Tech Lead: la enmienda va como apéndice al final de `docs/sdd/deRuedas-constitucion.md`**, que es lo que el Artículo 8 pide literalmente.

Con eso, la inmutabilidad de `docs/sdd/` admite **una excepción, y una sola**: el historial de enmiendas de la constitución, en modo *append-only*, tramitado por el Artículo 8. Ningún otro documento del corpus se toca, y de la constitución no se reescribe ni una palabra — solo se agrega al final.

> ⚠️ **Esto NO se ejecuta todavía.** `E-001` está en el paso (b) hasta el 20-ago. Lo decidido es **dónde** va a escribirse, no que ya se escribió. El texto está listo más abajo y se pega el día del cierre, después del paso (c).

Queda pendiente reflejar la excepción en la regla de inmutabilidad de `CLAUDE.md`/`AGENTS.md`, para que la próxima vez no vuelva a leerse como una contradicción. Va junto con el cierre del jueves.

<details>
<summary>Razonamiento original (las dos opciones que se evaluaron)</summary>

### El planteo

El Artículo 8 cierra diciendo:

> *"Las enmiendas se acumulan al final del documento como historial. La constitución original nunca se reescribe sin dejar rastro de las versiones previas."*

Pero `CLAUDE.md` declara `docs/sdd/` **corpus fuente inmutable**. Las dos reglas chocan: una manda escribir al final de `deRuedas-constitucion.md`, la otra prohíbe tocarlo.

| Opción | A favor | En contra |
|---|---|---|
| **A — Apéndice al final de `deRuedas-constitucion.md`** | Es lo que el Artículo 8 dice **literalmente**. Es **aditivo**: no reescribe nada y deja el rastro completo que el propio artículo exige. Por `ADR-000`, N0 gana sobre una convención de manejo. | Rompe la inmutabilidad de `docs/sdd/`, que existe para que lo derivado sea trazable a una fuente fija. |
| **B — Archivo aparte** (`docs/sdd/deRuedas-constitucion-enmiendas.md`) con puntero desde `E-001` | Preserva el corpus intacto. El historial queda igual de rastreable. | El Artículo 8 dice *"al final del documento"*, y esto no lo es. Requiere asumir el desvío. |

**Recomendación: opción A.** El Artículo 8 es N0 y la inmutabilidad de `docs/sdd/` es una convención operativa que no está en la jerarquía de `ADR-000`. Además el propósito de la inmutabilidad —que nada se reescriba en silencio— lo cumple igual un apéndice append-only, que es exactamente la forma que el artículo pide. Si se elige **B**, hay que registrarlo como desvío explícito.

</details>

---

## Artefacto para el paso (d) — texto de la enmienda

> Para pegar al final de `deRuedas-constitucion.md` (opción A) o en el archivo de enmiendas (opción B), **una vez aprobado el paso (c)**. Reemplazar `[FECHA]` y el decisor por lo que efectivamente ocurra.

```markdown
# Historial de enmiendas

## Enmienda 1 — Constitución v1.1

- **Fecha de registro**: [FECHA]
- **Propuesta**: E-001, abierta el 13-ago-2026
- **Discusión**: del 13 al 20-ago-2026 (cinco días hábiles, Artículo 8 paso b)
- **Aprobación**: decisión unipersonal del Tech Lead. El Artículo 8 prevé
  "mayoría calificada del equipo técnico y de producto"; ese cuerpo no existe
  hoy — el proyecto lo lleva una sola persona. Se registra lo que efectivamente
  ocurrió, no la forma prevista para un equipo que no hay.
- **Consulta a Dirección**: no requerida. La enmienda no afecta principios
  fundamentales: agrega una definición a la Parte IV sin modificar ninguna existente.
- **Motivo**: el corpus define once endpoints de administración de plataforma para un
  actor —el Super Admin— que el glosario nunca declaró, mientras `users.tenant_id` es
  FK NOT NULL. Son dos afirmaciones incompatibles dentro del mismo documento vinculante
  (IN-01, IN-02). Sin resolverlo, C-02 no puede escribir core/rbac.py, ni la migración
  inicial de users, ni los tests de autorización que plan-testing declara bloqueantes en CI.
- **Alcance**: Parte IV (Glosario y definiciones canónicas), **únicamente por adición**.
  Ninguna definición existente se modifica ni se elimina.

### Adición 1 — Nuevo término canónico: Super Admin

> **Super Admin**
>
> Persona del equipo de deRuedas con atribuciones de administración de la plataforma.
> **No es un Usuario**: no pertenece a ningún tenant y no aparece en el padrón de
> usuarios de ninguna agencia. Opera exclusivamente sobre los endpoints de
> administración de plataforma y sus acciones quedan registradas en la auditoría con su
> identidad propia. La distinción es sustantiva: un Usuario existe dentro de un tenant,
> un Super Admin existe por encima de todos.

### Adición 2 — Nota de equivalencia en la definición de Usuario

La definición de **Usuario** se conserva textualmente sin cambios. Se le agrega debajo,
como nota:

> *Nota de equivalencia.* Los identificadores de rol en código y en la base de datos son
> `manager` ≡ Gerente, `salesperson` ≡ Vendedor, `admin_staff` ≡ Administrativo. La
> interfaz de usuario emplea siempre los términos en español de este glosario.

### Qué queda intacto

| Definición vigente | Efecto de esta enmienda |
|---|---|
| *"Un usuario pertenece exactamente a un tenant"* | **Intacta.** `users.tenant_id` sigue NOT NULL. |
| *"Un usuario tiene un rol (Gerente, Vendedor, Administrativo)"* | **Intacta.** Siguen siendo esos tres. |

### Consecuencias registradas

- `user_role_enum` se crea con **tres** valores: `manager`, `salesperson`, `admin_staff`.
- Se crea la tabla `super_admins`, sin `tenant_id`, exenta de RLS.
- `users.tenant_id` permanece FK NOT NULL, sin excepciones.
- `audit_logs` referencia al actor de forma polimórfica: `(tipo_de_actor, id)`.
- Se desbloquean C-02 (bloque 6, T-014) y la matriz RBAC de ADR-024.
- ADR-017 deja de estar "aceptado condicionado" y pasa a aceptado pleno.
```

## Artefacto para el paso (e) — comunicación

> Para enviar **después** de registrada la enmienda. El envío es del usuario.

```
Asunto: Constitución v1.1 — se incorpora "Super Admin" al glosario canónico

La enmienda E-001, abierta el 13 de agosto, quedó registrada el [FECHA]. La
constitución pasa a versión 1.1.

QUÉ CAMBIA

Se agregan dos definiciones al glosario. No se modifica ni se elimina ninguna
existente.

1. "Super Admin" pasa a ser un término canónico. Es la persona del equipo de
   deRuedas que administra la plataforma. No es un Usuario: no pertenece a ningún
   tenant y no aparece en el padrón de ninguna agencia.

2. Se ratifica la equivalencia entre los identificadores de rol del código y los
   términos en español del glosario: manager = Gerente, salesperson = Vendedor,
   admin_staff = Administrativo. La interfaz siempre usa los términos en español.

QUÉ NO CAMBIA

Un usuario sigue perteneciendo exactamente a un tenant, y los roles de agencia
siguen siendo tres. La enmienda agrega; no toca lo que ya estaba.

POR QUÉ IMPORTA

El corpus ya definía once endpoints de administración de plataforma para un actor
que el glosario nunca había declarado. Eso bloqueaba el módulo de autorización, la
migración inicial de usuarios y la matriz de permisos. Con esto se destraba.

QUÉ HAY QUE HACER

Nada para la mayoría del equipo. Para quien toque backend: los tres valores de
user_role_enum son manager, salesperson y admin_staff; el Super Admin va en su
propia tabla, sin tenant_id y exenta de RLS. El detalle está en ADR-017 y en la
matriz canónica de ADR-024.

Texto completo de la enmienda: docs/adr/E-001-enmienda-glosario-super-admin.md
```

## Checklist del 20-ago

- [x] ~~Resolver el **obstáculo 1**~~ — ✅ 17-ago-2026: decisión unipersonal del Tech Lead
- [x] ~~Resolver el **obstáculo 2**~~ — ✅ 17-ago-2026: **opción A**, apéndice al final de la constitución
- [x] ~~Registrar en `CLAUDE.md`/`AGENTS.md` la **única excepción** a la inmutabilidad de `docs/sdd/`~~ — ✅ **19-ago-2026**, bajo la tabla de precedencia de los dos archivos, que son idénticos byte a byte. No esperaba al cierre: no es un paso del Artículo 8, es dejar de tener dos reglas que leídas sueltas se contradicen —una manda escribir al final de la constitución y la otra prohíbe tocarla—
- [x] ~~Anotar como pendiente la **enmienda al Artículo 8** para contemplar el decisor único~~ — ✅ **17-ago-2026**: no quedó anotada como pendiente, quedó **abierta** como [`E-002`](E-002-enmienda-articulo-8-decisor-unico.md), con cierre mínimo el 24-ago. No bloquea a `E-001` ni la condiciona
- [x] ~~Paso (c) — aprobación, asentada en la tabla de discusión~~ — ✅ **20-ago-2026**, decisión unipersonal del Tech Lead
- [x] ~~Paso (d) — pegar el texto de la enmienda con la fecha y el decisor reales~~ — ✅ **20-ago-2026**, apéndice al final de `deRuedas-constitucion.md`. Verificado que las 231 líneas originales quedaron **byte a byte idénticas**: el apéndice solo agrega
- [ ] Paso (e) — enviar la comunicación. ⚠️ **El envío es del usuario**, no del agente. El texto está listo en §*Artefacto para el paso (e)*; solo hay que reemplazar `[FECHA]` por el 20 de agosto de 2026
- [x] ~~Cambiar el **Estado** de este documento de 🟡 EN DISCUSIÓN a ✅ RATIFICADA~~ — ✅ **20-ago-2026**
- [x] ~~Quitar el *"aceptado condicionado a esta ratificación"* de [`ADR-017`](ADR-017-catalogo-de-roles-y-super-admin.md)~~ — ✅ **20-ago-2026**, aceptado pleno
- [x] ~~Desbloquear el **bloque 6 de C-02** (11 tareas)~~ — ✅ **20-ago-2026**: la tarea 6.1 de C-02 (*"verificar que `E-001` está ratificada; si no, detenerse acá"*) queda satisfecha y el portón se abre. Los **21 escenarios de `platform/authorization` siguen sin cerrar** — eso es la implementación, y es trabajo de C-02, no de esta enmienda
