# ADR-000 — Precedencia entre documentos del corpus vinculante

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead + Product Manager
- **Resuelve**: `PA-01` (prioridad Crítica) · valida `SU-12`
- **Alcance**: metadocumental — gobierna cómo se lee el corpus, no qué se construye

> Este ADR lleva el número **000** a propósito: precede a `ADR-001`…`ADR-012` porque
> establece el criterio con el que se leen esos mismos ADRs. No participa de la
> numeración en disputa de `IN-29`.

---

## Contexto

El corpus vinculante son 11 documentos en [`docs/`](../docs/). Al cruzarlos, la base de
conocimiento detectó **54 inconsistencias reales, 14 de ellas bloqueantes**. Ninguna es
visible leyendo un documento aislado.

`PA-01` preguntaba dos cosas: cuál es el orden de precedencia, y **cuál se escribió último**.
`SU-12` sostenía que la segunda pregunta era la decisiva — si las contradicciones fueran
versiones sucesivas de un mismo diseño que no se sincronizaron, resolverlas exigiría
arqueología, no criterio.

### Evidencia recogida

Los 11 documentos declaran en su texto *"Versión 1.0 — Mayo de 2026"*, y por eso se asumió
que la fecha no desempataba. **Los metadatos internos de los `.docx` originales
(`docProps/core.xml`) sí discriminan**, al milisegundo:

| # | Documento | `dcterms:created` (UTC) |
|---|---|---|
| 1 | `mejoras-y-saas` | 2026-05-06 17:31:39 |
| 2 | `historias-usuario` | 2026-05-06 17:52:16 |
| 3 | `constitucion` | 2026-05-06 18:05:22 |
| 4 | `spec-tecnica` | 2026-05-06 18:17:42 |
| 5 | `plan-implementacion` | 2026-05-06 21:48:47 |
| 6 | `plan-seguridad` | 2026-05-06 22:38:39 |
| 7 | `plan-testing` | 2026-05-06 23:17:22 |
| 8 | `brand-book` | 2026-05-07 00:00:05 |
| 9 | `plan-sre` | 2026-05-07 00:18:01 |
| 10 | `plan-gtm` | 2026-05-07 01:18:10 |
| 11 | `manual-usuario` | 2026-05-07 02:12:42 |

Los 11 tienen `cp:revision = 1` y `created == modified`: **nunca fueron editados después de
generarse**. El contraste lo confirma — `justificacion.docx` (no vinculante) es el único con
`created ≠ modified` y `dc:creator: Admin`, es decir, el único que tocó una persona.

En hora argentina, el corpus completo se produjo entre las **14:31 y las 23:12 del 6 de mayo
de 2026**: una sola sesión de 8 h 41 min.

### Qué se concluye de esa evidencia

1. **`SU-12` queda CONFIRMADO, no refutado.** Los 11 documentos sí están en el mismo momento
   de madurez.

2. **Por eso mismo, la recencia NO es un criterio de desempate válido.** El orden de los
   timestamps es orden de *generación*, no de *deliberación*. Aplicarlo daría resultados
   invertidos: `plan-gtm` (01:18) le ganaría a `spec-tecnica` (18:17) en pricing, y
   `manual-usuario` (02:12) le ganaría a todo, incluida la constitución (18:05).

3. **Las 54 contradicciones no son decisiones revisadas que no se propagaron** — que era el
   escenario de riesgo de `SU-12`. Son deriva de generación: cada documento se produjo sin
   verificación de consistencia contra los anteriores. **No hay una respuesta correcta oculta
   que recuperar.** Cada contradicción exige una decisión, no una investigación.

### La constitución ya declara su propia autoridad

El orden de precedencia **es derivable del corpus**; no hace falta inventarlo.
[`deRuedas-constitucion.md`](../docs/deRuedas-constitucion.md) habla de sí misma en cinco lugares:

| Ubicación | Qué establece |
|---|---|
| Preámbulo | Fija *"las bases inmutables"*, y aclara que **no** dice *"qué construir ni cómo construirlo en detalle —para eso están la especificación funcional y la especificación técnica"*. Se limita a sí misma. |
| Principio 4 | *"El mecanismo técnico vinculante para garantizar el aislamiento se especifica en el ADR correspondiente del documento de especificación técnica. Esta constitución solo establece el principio."* **Delega el "cómo" de forma explícita.** |
| Principio 5 | Los ADRs son vinculantes **hasta que un ADR posterior los reemplace**. Y: *"Las decisiones implícitas —es decir, las que se aplican sin haber sido documentadas— no son vinculantes."* |
| Artículo 8 | Procedimiento formal de enmienda: propuesta escrita, 5 días hábiles de discusión, mayoría calificada, registro con fecha y motivo, comunicación. |
| Parte IV (Glosario) | *"Las definiciones siguientes son canónicas para el proyecto. Cuando un término aparece en cualquier documento, código, comunicación o interfaz, se asume con el significado aquí establecido. **Las divergencias se tratan como errores y se corrigen.**"* |

---

## Decisión

Se adopta una **jerarquía por autoridad, con competencia por dominio**. La fecha de creación
de los documentos **no se usa como criterio de desempate en ningún caso**.

### Niveles

| Nivel | Documentos | Autoridad | Cómo se modifica |
|---|---|---|---|
| **N0** | `constitucion` | Principios, reglas vinculantes y **glosario canónico**. Gana sobre todos los niveles, siempre. | Solo por **enmienda formal del Artículo 8** |
| **N1** | `spec-tecnica` + los ADRs | El **"cómo"** técnico: modelo de datos, contratos de API, arquitectura. Autoridad **delegada explícitamente por N0**. | Por ADR posterior (Principio 5) |
| **N2** | `plan-implementacion` | **Orden, secuenciación y descomposición** en tareas `T-XXX`. No tiene autoridad sobre el diseño. | Actualización del roadmap |
| **N3** | `plan-seguridad`, `plan-testing`, `plan-sre` | Detalle **dentro de su dominio propio**. Ver la regla de competencia, abajo. | ADR o actualización del plan |
| **N4** | `plan-gtm`, `manual-usuario`, `brand-book`, `mejoras-y-saas`, `historias-usuario` | **No normativos** para el diseño técnico. Son insumo, intención comercial o descripción. | — |

### Regla de competencia por dominio

> **Un documento N3 prevalece sobre N1 dentro de su dominio propio, y nunca sobre N0.**

Dominios propios:

- `plan-seguridad` → controles de seguridad, modelo de amenazas, compliance
- `plan-testing` → estrategia de pruebas, pirámide, quality gates
- `plan-sre` → SLOs, alertas, runbooks, RTO/RPO, capacidad

Fuera de su dominio, un N3 vale como N4: informativo.

**Toda aplicación de esta regla se registra como ADR.** Un desvío de N1 sin ADR es una
decisión implícita y, por el Principio 5, no es vinculante.

### Reglas de aplicación

1. **N0 nunca pierde.** Si la respuesta técnicamente correcta contradice a N0, no se
   "resuelve": se **enmienda** por el Artículo 8. La diferencia no es formal — cambia quién
   decide y con qué procedimiento.
2. **El glosario de N0 es canónico sobre todo el corpus.** Un término usado con otro
   significado en cualquier documento es un error a corregir, no una alternativa a evaluar.
3. **Empate de nivel ⇒ la regla no decide.** Cuando dos documentos del mismo nivel se
   contradicen, esta jerarquía es muda y la contradicción **escala al decisor humano**
   indicado en `PA-XX`. No se elige por antigüedad, ni por extensión, ni por especificidad.
4. **Lo no escrito no es vinculante** (Principio 5). Un vacío documental es un riesgo abierto
   (`R-X`), no una licencia para inferir.

---

## Consecuencias

### Contradicciones que esta regla resuelve de forma mecánica

| ID | Conflicto | Resolución | Por qué |
|---|---|---|---|
| `IN-22` | Cobertura del quality gate: 80 % (N0) vs 70/60 (`plan-testing`, N3) | **80 %** | N3 nunca gana sobre N0, ni siquiera en su dominio propio. Coincide con la regla dura 5 ya vigente. |
| `IN-29` | Numeración de ADRs: `spec-tecnica` (N1) vs `plan-implementacion` (N2) | **Manda la numeración de la spec.** Se corrigen las referencias del plan. | N1 > N2. La spec *contiene* los ADRs; el plan solo los referencia. |
| `IN-31` | SLA: 99.9/99.9/99.95 (`spec-tecnica`, N1) vs 99.0/99.5/99.9 (`plan-sre`, N3 + `plan-gtm`, N4) | **99.0 / 99.5 / 99.9** | Competencia de dominio: disponibilidad y SLOs son dominio propio de SRE. Resuelve además la insostenibilidad de un SLA superior al SLO interno de 99.7 %. |

### Contradicciones que esta regla NO resuelve — y por qué importa

Este es el resultado más útil del ADR: **identifica dónde la jerarquía es muda**, en vez de
fingir que decide.

| ID | Situación | Qué se necesita |
|---|---|---|
| `IN-01` | El glosario N0 fija **3 roles en español**; el catálogo operable son **4 en inglés** (`super_admin` incluido). La regla 2 hace ganar a N0 — y eso rompe `T-014`, la matriz RBAC y los tests de autorización. | **Enmienda del Artículo 8**, no una resolución. Decisor: Tech Lead + equipo. |
| `IN-03`, `IN-04` | `mejoras-y-saas` vs `plan-gtm`: **ambos son N4**. Empate de nivel. | Escala a **Dirección** / Product Manager (`PA-03`, `PA-04`). |
| `IN-07` | `domain_plate NOT NULL` (N0 + N1) vs nullable (N2, `plan-implementacion`). N0/N1 ganan — pero un 0 km o una permuta recién recibida no tienen patente. | Decisión de negocio, y **enmienda** si se opta por nullable (`PA-13`). |
| `IN-13` | Retención de `audit_logs`: 5 años (N1, con invocación legal) vs 24 meses (N3 seguridad + SRE). Competencia de dominio haría ganar a N3, pero N1 invoca una obligación legal externa al corpus. | **Legal + Tech Lead** (`PA-05`). La regla no puede zanjar una obligación legal. |

### Consecuencias operativas

- ✅ Queda un criterio único, escrito y vinculante para leer las 54 inconsistencias.
- ✅ Se descarta explícitamente la recencia, evitando un error que habría invertido varias
  resoluciones (pricing, SLA, alcance del MVP).
- ✅ Cada change de [`CHANGES.md`](../CHANGES.md) puede resolver sus `IN-XX` sin reabrir la
  discusión de fondo.
- ⚠️ **Aparecen enmiendas formales pendientes** (`IN-01`, potencialmente `IN-07`). El
  Artículo 8 exige 5 días hábiles de discusión: hay que **abrirlas ya** para que no bloqueen
  `C-02` y `C-14`.
- ⚠️ Los ADRs nuevos viven en [`decisions/`](.). La spec técnica es el corpus fuente y no se
  edita. **`C-01` debe formalizar** esta convención junto con la corrección de `IN-29`.

---

## Alternativas consideradas

**Jerarquía estricta, sin competencia por dominio.** Más simple y mecánica, resuelve todo sin
reuniones. Descartada porque fuerza resultados operativamente insostenibles: en `IN-31`
habría hecho ganar a la spec (99.9/99.9/99.95) contra un SLO interno de 99.7 % — un SLA
imposible de cumplir, comprometido desde el día uno.

**Solo `constitucion` + `spec-tecnica` normativos, los otros 9 informativos.** Máxima
simplicidad. Descartada porque tira trabajo real y específico: el modelo STRIDE de
`plan-seguridad`, la pirámide de pruebas de `plan-testing`, y los runbooks y objetivos
RTO/RPO de `plan-sre` no están en ningún otro documento.

**Recencia (el último escrito gana).** Descartada **por evidencia**, no por criterio: los
timestamps reflejan orden de generación dentro de una única sesión, y aplicarlos invertiría
la autoridad real del corpus. Ver la sección de Contexto.
