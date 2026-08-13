# ADR-014 — Umbrales de cobertura: 80 % líneas / 60 % ramas

- **Estado**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead
- **Resuelve**: `IN-22`
- **Afecta**: `C-01` (T-003), `.github/workflows/ci.yml`, `pyproject.toml` (`[tool.coverage]`), y todo change posterior
- **Naturaleza**: **aplicación de [`ADR-000`](ADR-000-precedencia-documental.md) sobre un conflicto de cuatro fuentes**, más una decisión propia sobre ramas donde N0 guarda silencio. Enmienda al plan de testing (N3); **no** enmienda a la constitución.

---

## Contexto

`IN-22` es una de las 14 inconsistencias bloqueantes: **cuatro documentos dan cuatro umbrales de cobertura distintos**, y el pipeline de `T-003` no se puede escribir sin saber cuál manda.

| Documento | Nivel | Qué dice, textual |
|---|---|---|
| `constitucion` Art. 2 (§87) | **N0** | *"La cobertura mínima del código backend es ochenta por ciento medida sobre líneas, y la cobertura no decrece entre commits, salvo que medie una excepción documentada."* |
| `spec-tecnica` §1510 | N1 | *"mínimo 80 % para módulos core (auth, stock, crm, communication, finance), 70 % para los demás"* |
| `plan-implementacion` §1021 (job `test-backend-unit`) | N2 | *"pytest -m 'not integration' con coverage. Mínimo 80 % global."* |
| `plan-testing` §127, §659, §661 | N3 | *"70 % líneas, 60 % branches en código de dominio"* · branches *"no inferior a 60 % en módulos críticos"* |

## Decisión

**80 % de líneas y 60 % de ramas, ambos globales sobre el backend, como piso duro bloqueante en CI.**

### Líneas: 80 %, y no hay discusión

`ADR-000` no cuenta documentos, reparte autoridad. **N0 dice 80 % de líneas sobre el backend, global.** N0 nunca pierde: no se resuelve por mayoría ni por especificidad.

Y acá ni siquiera hace falta invocar la regla con fuerza, porque las fuentes convergen casi solas:

- **N2 coincide exactamente** con N0: 80 % global.
- El **80 % core de N1 es compatible** — un piso global del 80 % lo satisface por construcción.
- El **70 % resto de N1 queda por debajo del piso de N0** y se descarta.
- El **70 % de N3 sale de un solo documento**, y `plan-testing` no prevalece sobre N0 ni siquiera dentro de su dominio propio. Esa es la mitad de la regla de competencia que se cita menos y que importa igual: un N3 llena vacíos de N0, no rebaja sus pisos.

### Ramas: 60 %, y acá sí gobierna N3

**La constitución no se pronuncia sobre cobertura de ramas.** Ni la spec técnica ni el plan de implementación tampoco. La única fuente que habla del tema es `plan-testing`, y las ramas son dominio propio de testing.

Ante el silencio de N0, la regla de competencia por dominio de `ADR-000` funciona exactamente como corresponde: **gobierna N3**. No rebaja nada, cubre un vacío.

### La generalización, dicha con todas las letras

`plan-testing` acota sus dos umbrales por alcance: 70 % de líneas *"en código de dominio (excluye infraestructura, generated code, migrations)"* y 60 % de ramas *"en módulos críticos (auth, leads, conversaciones, billing futuro)"*.

**Este ADR aplica el 60 % de ramas globalmente, no solo a los módulos críticos.** Es una decisión propia y hay que decirla, no dejarla pasar como si viniera del plan de testing.

Razones:

1. **Un gate por lista de módulos es un gate que se pudre.** Cada módulo nuevo obliga a acordarse de agregarlo a la lista de críticos. El día que alguien se olvida, el módulo entra sin control de ramas y nadie se entera.
2. **Un solo número es auditable de un vistazo.** Dos umbrales con dos alcances distintos son cuatro cosas para verificar en cada revisión.
3. **Es más estricto, nunca más laxo.** Un piso global del 60 % implica el 60 % en los módulos críticos. No hay forma de que esta generalización deje pasar algo que el plan de testing habría frenado.

El costo asumido: módulos de infraestructura con mucha ramificación defensiva y poco valor de negocio van a tener que testearse o excluirse explícitamente. Se prefiere la exclusión **explícita y auditable** por sobre el umbral laxo — es la misma lógica que la mitigación de riesgo de [`design.md`](../../openspec/changes/foundation-setup/design.md) para el scaffolding.

### La cobertura no decrece

Además del piso absoluto, el pipeline verifica que **la cobertura no baje respecto de `main`**. Sale de N0 (Art. 2) y N1 (§1512) diciendo lo mismo, y es el control que impide la degradación lenta: cada PR pasa el 80 %, pero de a poquito el número se va cayendo hasta apoyarse en el piso.

Una excepción **documentada** puede levantar el bloqueo, como establece el Art. 2. Documentada quiere decir escrita en el PR con su motivo, no un flag en el pipeline.

## Consecuencias

- **`plan-testing` queda enmendado** en sus §127, §659 y §661: 70 % → 80 % en líneas, y el 60 % de ramas se generaliza de módulos críticos a global. **No se edita el documento**: es corpus fuente inmutable. Este ADR es el registro, y el Principio 5 establece que un ADR posterior reemplaza lo anterior.
- **La constitución no se toca.** Este es el punto que hace que la decisión sea barata: si hubiera que bajar el piso a 70 % habría que enmendar N0 por el Artículo 8 — cinco días hábiles de discusión y otro decisor. Como el resultado *coincide* con N0, no hay enmienda constitucional que tramitar.
- **El gate de CI es bloqueante**, no informativo: 80 % de líneas, 60 % de ramas, y no decrece. Un PR que falle cualquiera de los tres no se mergea (`T-003`, tarea 8.2).
- **Las exclusiones de cobertura se declaran una por una** en `pyproject.toml`, con comentario. Nada de `omit` con comodines amplios: una exclusión que nadie puede auditar es un agujero con permiso.
- **Riesgo conocido en C-01**: sobre un repositorio casi vacío, cualquier línea sin cubrir pesa muchísimo. Por eso el scaffolding sin lógica (`__init__.py`, `alembic/env.py`) se excluye explícitamente desde el primer commit.
- **El umbral aplica al backend.** El frontend corre `vitest` con cobertura en su propio job, sin gate numérico en C-01: ninguna de las cuatro fuentes fija un piso para frontend, y este ADR no inventa uno. Queda como pregunta abierta para C-07.

## Alternativas consideradas

**70 % líneas / 60 % ramas, siguiendo el plan de testing.** Es el umbral más realista para arrancar y el que propone la fuente que más sabe de testing. Descartada porque **contradice a N0**, y contradecir a N0 no se resuelve por ADR — se enmienda la constitución por el Artículo 8. Distinto procedimiento y distinto decisor. No era una opción disponible para el Tech Lead.

**80 % core / 70 % resto, siguiendo la spec técnica.** Reconoce que no todo el código merece el mismo rigor. Descartada por dos motivos: el 70 % queda bajo el piso de N0, y la clasificación core/resto es una lista que hay que mantener a mano, con el mismo problema de pudrición que la lista de módulos críticos.

**Sin gate de ramas, solo líneas.** Simplifica el pipeline y evita el debate del alcance. Descartada porque la cobertura de líneas sola es la métrica más fácil de inflar: un test que recorre una función con `if/else` sin ejercitar ambas ramas suma líneas y no prueba nada. El propio `plan-testing` §47 advierte que la cobertura es *"una métrica útil pero engañosa"*, y el gate de ramas es justamente lo que la vuelve menos engañosa.
