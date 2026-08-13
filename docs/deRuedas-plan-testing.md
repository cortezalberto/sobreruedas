**Plan de Testing**

**y Aseguramiento de Calidad**

***deRuedas Gestión***

Estrategia piramidal, automatización, ambientes,

métricas y criterios de release

*Verificación del trabajo del agente de IA · Roadmap de madurez*

Versión 1.0 — Mayo de 2026

**1. Introducción y propósito**

Este documento es complementario al cuerpo SDD de deRuedas Gestión y se ocupa de una dimensión que las cinco capas canónicas tocan tangencialmente pero no consolidan: el aseguramiento de la calidad del producto. La constitución declara la calidad como compromiso; la spec técnica menciona estrategia de testing en cada dominio; el plan de implementación incluye tareas de testing distribuidas; el plan de seguridad cubre los aspectos defensivos. Pero ninguno de esos documentos consolida en un solo lugar la estrategia integral: qué se testea, en qué nivel, con qué herramientas, contra qué criterios, en qué ambientes, con qué métricas y bajo qué responsabilidades. Este documento llena ese vacío.

La existencia del documento se justifica por tres razones convergentes. La primera es comercial: las agencias medianas y grandes que evaluarán contratar deRuedas van a preguntar cómo se asegura la calidad antes de confiar la operación crítica de su negocio a un SaaS recién aparecido en el mercado. La segunda es operativa: sin estrategia explícita de testing los esfuerzos se distribuyen ad hoc y aparecen los síntomas clásicos —tests donde son fáciles de escribir y faltan donde son críticos, regresiones que sorprenden, cobertura que parece alta pero no protege— que erosionan la confianza del equipo en su propio producto. La tercera es metodológica: en un proceso de desarrollo asistido por IA donde un agente produce código rápidamente, el testing es la principal red de seguridad humana sobre el trabajo del agente; sin estrategia explícita el agente puede entregar código que pasa los tests que él mismo redactó pero falla en escenarios que ningún humano previó.

**1.1 Audiencia**

El documento tiene cuatro audiencias diferenciadas. Para el equipo de desarrollo —incluyendo el agente de IA cuando ejecuta tareas del plan— funciona como referencia normativa de qué tests son obligatorios para cada tipo de trabajo, qué cobertura se exige, qué quality gates impide promover una rama. Para customer success y soporte funciona como mapa de qué garantías de calidad puede prometer al tenant y qué procesos están vigentes para detectar y corregir defectos. Para auditores externos funciona como evidencia documental de que la organización tiene procesos maduros de aseguramiento de calidad, no improvisación. Para tenants enterprise que pidan visibilidad sobre el proceso de QA del proveedor funciona como documento entregable bajo NDA.

**1.2 Alcance**

El alcance del documento abarca todas las dimensiones de calidad del producto deRuedas Gestión: funcionalidad correcta, aislamiento multi-tenant (crítico para este producto), seguridad y autorización, performance bajo carga esperada, resiliencia ante fallos de dependencias, privacidad en el manejo de datos personales, accesibilidad y compatibilidad de los frontends, regresión sostenida a lo largo de releases. Quedan fuera del alcance las pruebas de aceptación que cada tenant ejecuta sobre su propia configuración —son responsabilidad del tenant según la matriz de responsabilidad compartida del Plan de Seguridad— y las pruebas que terceros realizan sobre integraciones externas que el producto consume (WhatsApp Cloud API, portal deRuedas).

**1.3 Posición frente al cuerpo SDD**

El plan de testing no reemplaza ni contradice las decisiones del cuerpo SDD: las extiende. Cuando hay solapamiento con la spec técnica —por ejemplo, la spec menciona que cierto endpoint debe tener tests de aislamiento— este documento profundiza qué significa exactamente y cómo se materializa. Cuando hay solapamiento con el plan de seguridad —por ejemplo, los tests de control de acceso que prueban controles como C2.1 RBAC— este documento adopta los mismos identificadores y los amplía con detalles del cómo. Cuando una tarea del plan de implementación tiene definition of done que incluye “tests verdes”, este documento define qué cuenta como “verde” según el tipo de tarea.

**1.4 Estructura del documento**

El documento está organizado en doce capítulos. El segundo capítulo desarrolla los principios y la filosofía del programa de calidad: cómo se piensa el testing, qué se prioriza, qué anti-patrones se evitan. El tercero presenta la estrategia piramidal por niveles desde unit hasta E2E. El cuarto desarrolla los tipos de testing por dimensión —funcional, aislamiento multi-tenant, seguridad, performance, resiliencia, privacidad, accesibilidad— con su tratamiento específico. El quinto cubre la gestión de datos de prueba. El sexto define los ambientes y las promociones entre ellos. El séptimo detalla la automatización y los pipelines. El octavo aborda la cuestión específica de cómo verificar el trabajo del agente de IA. El noveno declara las métricas del programa. El décimo define los roles y responsabilidades. El décimo primero establece criterios de release. El décimo segundo cubre la gestión de defectos. Cierra el documento un capítulo de roadmap de madurez y anexos con plantillas y glosario.

**2. Principios y filosofía del programa**

Esta sección declara cómo el equipo piensa el testing. Las decisiones técnicas y operativas posteriores se filtran contra estos principios. Algunos son directamente derivables de la constitución del producto; otros son específicos de la dimensión de calidad y se introducen aquí. Como en el resto del cuerpo SDD, los principios no son aspiracionales sino accionables: cada uno tiene formulación que permite evaluar si una decisión concreta lo respeta o lo viola.

**2.1 Principio Q1 — El testing es propiedad del producto, no actividad separada**

Una funcionalidad sin tests no es funcionalidad: es una hipótesis. Los tests son parte del entregable, no un anexo opcional. Esto tiene tres consecuencias prácticas. La definición de done de cualquier tarea del plan de implementación incluye los tests correspondientes. El concepto de “terminado y queda el testing pendiente” no existe en el método. Y el código de tests recibe los mismos cuidados que el código de producción: legibilidad, refactorización, eliminación de duplicación, mantenibilidad.

**2.2 Principio Q2 — Confianza sobre cobertura**

La cobertura es una métrica útil pero engañosa. Un sistema con 95% de cobertura puede ser indistinguible de uno con 60% si los tests del primero ejercitan caminos triviales y los del segundo cubren los escenarios críticos. El programa adopta como criterio principal la confianza, definida operacionalmente como la probabilidad subjetiva del equipo de que un cambio mergeado no rompió nada relevante. La cobertura se monitorea pero como salud del programa, no como objetivo en sí. Los esfuerzos se distribuyen donde aumentan la confianza, no donde aumentan el número.

**2.3 Principio Q3 — Shift-left testing**

Los defectos son progresivamente más caros de corregir cuanto más tarde se descubren: el orden creciente de costo es desarrollo local, code review, CI, staging, producción, soporte. La estrategia es empujar la detección lo más a la izquierda posible. Esto se materializa en tests unitarios rápidos ejecutables localmente, validación temprana en pre-commit hooks, integración continua que corre en cada PR antes del merge, ambientes que reciben verificación automática antes de promoverse. La filosofía contraria, que delega el testing a una fase de QA al final del ciclo, queda explícitamente descartada.

**2.4 Principio Q4 — Automatización por defecto, manual por excepción**

Todo test que pueda automatizarse debe automatizarse. La justificación no es ideológica sino económica: un test automatizado se ejecuta cientos de veces al año a costo marginal cero; un test manual exige una persona cada vez. Las excepciones legítimas son tres: tests exploratorios (donde el valor está en el descubrimiento humano de lo no anticipado), tests de aceptación de usuario (donde el cliente debe verificar que la solución resuelve su dolor), y tests de UX (donde la apreciación cualitativa humana no es reemplazable). Cualquier test fuera de esas tres categorías debería poder automatizarse y, si no se hace, debe haber justificación explícita.

**2.5 Principio Q5 — Tests deterministas**

Un test que falla a veces sí, a veces no, es peor que un test ausente: erosiona la confianza en toda la suite. La política es cero tolerancia a flaky tests. Cuando un test exhibe comportamiento intermitente se hace una de dos cosas: se corrige la fuente de no determinismo (timing, recursos compartidos, datos persistentes entre tests, dependencias externas), o se elimina. Lo que no se hace es marcarlo como ignored y olvidarlo: un test ignored es ruido que opaca señal. La métrica de flakiness se monitorea por suite y dispara alertas cuando supera el threshold.

**2.6 Principio Q6 — Pirámide invertida descartada**

Algunos equipos privilegian tests E2E porque “prueban el sistema completo como el usuario lo usa” y minimizan unit tests. La pirámide invertida funciona en proyectos chicos pero escala mal: los E2E son lentos, frágiles, caros de mantener y producen señales difusas (cuando un E2E falla rara vez se sabe inmediatamente cuál componente lo rompió). La estrategia adoptada es la pirámide tradicional: amplia base de unit tests rápidos, capa intermedia de integration y contract tests, cima estrecha de E2E sobre flujos críticos. Las proporciones objetivo se discuten en la sección 3.

**2.7 Principio Q7 — Tests escritos junto al código, no después**

La práctica adoptada es escribir tests al mismo tiempo que el código de producción, idealmente con un patrón cercano a TDD aunque sin dogmatismo. La justificación es doble: escribir tests durante el desarrollo expone problemas de diseño que la mente del desarrollador todavía tiene presente; escribirlos después convierte al testing en tarea ingrata que se hace con prisa y se descubre incompleta. La política es que un PR sin tests para el código nuevo se devuelve sin discusión salvo que el cambio sea trivial documentado o configuración pura.

**2.8 Principio Q8 — Tests como documentación viva**

Un test bien escrito es la mejor documentación posible del comportamiento esperado de una función o un componente. Esto impone una exigencia adicional sobre el código de tests: los nombres deben describir qué se está verificando en lenguaje del dominio (no “test_001” sino “test_lead_marked_won_creates_audit_entry”); el cuerpo del test debe leerse como una historia (arrange, act, assert) sin abstracción gratuita; los datos de prueba deben ser realistas. Tests escritos así sirven a un nuevo desarrollador o al agente de IA cuando necesita entender qué hace un módulo: leer los tests es más rápido y más confiable que leer la implementación.

**2.9 Principio Q9 — Aislamiento multi-tenant es testing de primera clase**

Para deRuedas, dada su naturaleza multi-tenant declarada en la constitución (P1), el aislamiento entre tenants no es un test más: es categoría propia con bloqueo absoluto. Una falla en aislamiento no es defecto: es violación del compromiso central del producto. La política es que los tests de aislamiento son obligatorios para todo módulo que toque datos del tenant, son bloqueantes en CI, y su ejecución es introspectiva (no se puede agregar tabla con tenant_id sin que CI verifique también su política RLS y sus tests de aislamiento).

**2.10 Postura frente al testing del agente de IA**

El agente de IA produce código y produce los tests que acompañan ese código. Este hecho introduce un riesgo metodológico: el agente puede escribir tests que confirman lo que él mismo construyó, no lo que el comportamiento esperado exige. La política compensa este riesgo por dos vías. La primera es que los criterios de aceptación de cada tarea del plan están escritos antes de la ejecución (como parte del Definition of Done de la capa 5 del SDD): el agente debe satisfacerlos, no inventarlos. La segunda es que los tests producidos por el agente reciben revisión humana específica enfocada no solo en “son correctos” sino en “cubren los escenarios que un humano hubiera pensado”. Este aspecto se desarrolla en el capítulo 8.

**Resumen operativo:** Los nueve principios anteriores se condensan en una idea: el testing no es un costo del proyecto sino una propiedad inseparable del producto, ejecutada lo más temprano y automáticamente posible, con disciplina sobre flakiness y especial cuidado en las dimensiones que la constitución del producto declara como críticas (multi-tenancy, auditabilidad, privacidad).

**3. Estrategia piramidal por niveles**

Esta sección define cómo se distribuye el esfuerzo de testing entre niveles, qué se testea en cada uno, qué herramientas se usan y qué tiempos de ejecución se admiten. La pirámide canónica adoptada tiene cuatro niveles operativos: unit, integration, contract y E2E. Por encima de la pirámide automatizada hay un quinto nivel manual, exploratorio, que cumple funciones específicas no automatizables.

**3.1 La pirámide en una vista**

╱╲

╱ ╲

╱ E2E╲ ~5% lentos, frágiles

╱──────╲ críticos negocio

╱Contract╲ ~10% contratos APIs

╱──────────╲ y eventos

╱ Integration ╲ ~25% servicios + DB

╱──────────────╲ sin externos

╱ Unit ╲ ~60% rápidos, masivos

╱─────────────────── ╲ base ancha

─────────────────────────

exploratorio manual / UAT / accesibilidad / UX

(no en la pirámide, pero parte del programa)

**3.2 Nivel 1 — Unit tests**

**Qué prueban:** lógica de una unidad aislada (función, método, clase, componente UI)

**Qué NO prueban:** interacción real con base, red, archivos, otros servicios

**Tiempo objetivo:** \<5 ms por test; suite completa \<60 segundos

**Herramientas backend:** pytest + pytest-asyncio + factory-boy + faker

**Herramientas frontend:** Vitest + React Testing Library + msw para mocks de red

**Cobertura objetivo:** 70% líneas, 60% branches en código de dominio; menor en código de infraestructura

**Qué se testea en unit**

Los unit tests verifican la lógica pura del código: cálculos, transformaciones, validaciones, decisiones de control de flujo, manejo de casos límite y errores. Los inputs son fijos, los outputs se afirman explícitamente, las dependencias externas se reemplazan por test doubles (mocks, stubs, fakes según corresponda). Lo que se testea, en orden de prioridad: primero las reglas de dominio (lo que un experto del negocio reconocería como conducta esperada), después los casos límite y errores (qué pasa con cero elementos, con valores nulos, con inputs malformados), después la integración entre piezas chicas que sí pueden testearse juntas sin tocar infraestructura.

**Qué NO se testea en unit**

Lo que requiere base de datos, broker de eventos, llamadas HTTP reales o sistema de archivos no se testea en unit. Esos elementos van a integration. La tentación común es mockear la base de datos para escribir “unit tests” que ejercitan código que toca la base: el resultado es un test que pasa pero no garantiza nada porque las queries reales contra la BD nunca se ejecutaron. La regla es estricta: si el código bajo prueba interactúa con un servicio externo o con un recurso compartido, el test no es unit.

**Estructura de un unit test**

\# tests/unit/leads/test_lead_won_validations.py

import pytest

from leads.domain import Lead, LeadStatus, mark_lead_as_won

from leads.errors import VehicleAlreadySoldError

from tests.factories import make_lead, make_vehicle

class TestMarkLeadAsWon:

def test_marks_lead_as_won_when_vehicle_available(self):

lead = make_lead(status=LeadStatus.QUALIFIED)

vehicle = make_vehicle(status='available')

result = mark_lead_as_won(lead, vehicle, sale_amount=15_000_000)

assert result.lead.status == LeadStatus.WON

assert result.vehicle.status == 'sold'

assert result.sale_amount == 15_000_000

def test_rejects_when_vehicle_already_sold(self):

lead = make_lead(status=LeadStatus.QUALIFIED)

vehicle = make_vehicle(status='sold')

with pytest.raises(VehicleAlreadySoldError) as exc:

mark_lead_as_won(lead, vehicle, sale_amount=15_000_000)

assert 'consultar al manager' in str(exc.value)

def test_records_sale_metadata_for_audit(self):

\# ... etc

**3.3 Nivel 2 — Integration tests**

**Qué prueban:** interacción del código con servicios reales: PostgreSQL, Redis, S3 local

**Qué NO prueban:** servicios externos genuinos (Meta, gateway pagos): se usan stubs

**Tiempo objetivo:** \<2 segundos por test; suite completa \<10 minutos

**Herramientas:** pytest + testcontainers (PG, Redis, MinIO) + httpx para llamadas a la API

**Cobertura:** principales caminos de cada endpoint y de cada consumer de eventos

**Qué se testea en integration**

Los integration tests ejercitan el código contra infraestructura real (en versión local o en contenedores efímeros). Verifican que las queries de SQLAlchemy producen los resultados esperados contra el motor real de PostgreSQL, que las migraciones funcionan, que las políticas RLS efectivamente filtran, que los eventos publicados son consumidos por los handlers correctos, que los uploads a storage funcionan. Los servicios externos genuinos se reemplazan por stubs que reproducen su contrato pero corren localmente.

**Estructura de un integration test**

\# tests/integration/leads/test_lead_endpoints_integration.py

import pytest

from httpx import AsyncClient

@pytest.mark.asyncio

async def test_post_lead_creates_record_and_emits_event(

client: AsyncClient,

tenant_a_user,

db_session,

event_stream

):

payload = {'contact_id': 'c-001', 'vehicle_interest_id': 'v-100'}

response = await client.post(

'/api/v1/leads',

json=payload,

headers=tenant_a_user.auth_headers(),

)

assert response.status_code == 201

lead_id = response.json()\['id'\]

\# Verificación contra BD real

db_lead = await db_session.get(Lead, lead_id)

assert db_lead.tenant_id == tenant_a_user.tenant_id

\# Verificación contra stream real

events = await event_stream.read_events('leads', count=1)

assert events\[0\].type == 'lead.created'

assert events\[0\].payload\['lead_id'\] == lead_id

**3.4 Nivel 3 — Contract tests**

**Qué prueban:** que las APIs y eventos respetan su contrato declarado

**Por qué importa:** los consumidores (frontend, integradores externos, otros módulos) dependen de que el contrato no rompa silenciosamente

**Herramientas:** schemathesis para APIs OpenAPI; tests dedicados para schemas de eventos

**APIs**

La spec OpenAPI generada por FastAPI es la fuente de verdad del contrato. Los contract tests verifican que los endpoints en ejecución responden con los schemas declarados, que los códigos de status son los documentados, que los campos requeridos están presentes, que los tipos coinciden. Schemathesis se ejecuta contra el server en staging cada noche y bloquea el merge cuando detecta divergencia entre lo declarado y lo entregado. Cualquier cambio incompatible al contrato (eliminar campo, cambiar tipo) requiere versionado explícito de la API.

**Eventos**

Los eventos publicados al stream tienen schema versionado. Los tests verifican que el publisher emite eventos válidos contra el schema vigente y que los consumers aceptan eventos de versiones declaradas como compatibles. La política es backward compatible por default: los productores pueden agregar campos opcionales sin romper consumers, los consumers no pueden asumir campos no declarados como requeridos.

**3.5 Nivel 4 — End-to-End tests**

**Qué prueban:** flujos completos del usuario atravesando el sistema entero

**Tiempo objetivo:** suite E2E completa \<30 minutos; flujos críticos selectos \<5 minutos

**Herramientas:** Playwright para frontend web; Detox o Maestro para mobile

**Cobertura:** 5 a 15 flujos críticos del producto, no más

**Cuándo usar E2E**

Los E2E son caros: lentos de ejecutar, frágiles ante cambios de UI, difíciles de debuggear cuando fallan. Se reservan para los flujos cuya rotura tendría impacto comercial inmediato y que son intrínsecamente integrales (involucran múltiples componentes que tests más bajos no podrían atrapar). Los flujos típicamente cubiertos son: alta de tenant + onboarding + primer lead; flujo de WhatsApp end-to-end (mensaje entrante → conversación → respuesta saliente); cierre de venta completo desde lead hasta dashboard actualizado; export de datos del tenant para portabilidad. Cualquier flujo nuevo candidato a E2E requiere justificación de por qué no podría cubrirse con integration tests más rápidos.

**Patrón de E2E robusto**

Los E2E son frágiles cuando dependen de selectors basados en estructura de UI (XPath complicados, clases CSS, posiciones absolutas). La política adoptada es que toda interacción E2E usa selectors semánticos —data-testid, roles ARIA, texto visible— que los desarrolladores aceptan como parte del contrato del componente. Cambiar un componente sin actualizar su data-testid es responsabilidad del PR del cambio, no del equipo de QA. Esto neutraliza la causa más común de flakiness en E2E.

**3.6 Nivel 5 — Manual exploratorio**

La automatización no reemplaza el ojo humano para descubrir problemas que nadie anticipó. El programa adopta sesiones de testing exploratorio con tres modalidades. Sesiones internas semanales donde un miembro del equipo se sienta a usar el producto sin script con el rol de un usuario real durante una hora, registrando hallazgos. Sesiones de “bug hunt” antes de cada release significativa con todo el equipo. Sesiones con tenants reales en early adopter program durante el primer mes de uso, incentivadas con descuento por feedback estructurado. Los hallazgos entran como bugs en el sistema de tracking y se priorizan según el proceso del capítulo 12.

**3.7 Cobertura objetivo total**

|  |  |  |  |
|:---|:---|:---|:---|
| **Tipo** | **Cobertura código** | **% del total tests** | **Tiempo ejec. suite** |
| Unit | 70% líneas en dominio, 60% branches | ~60% | \<60 segundos |
| Integration | Endpoints principales y consumers | ~25% | \<10 minutos |
| Contract | 100% endpoints y eventos publicados | ~10% | \<5 minutos |
| E2E | 5-15 flujos críticos | ~5% | \<30 minutos |

**Sobre los porcentajes:** Los porcentajes son orientativos y se revisan trimestralmente con datos reales del proyecto. La distribución exacta debe ajustarse al contexto: módulos con lógica de dominio densa requieren más unit; módulos con muchas integraciones requieren más integration. La pirámide es una guía, no una camisa de fuerza.

**4. Tipos de testing por dimensión**

Los niveles de la pirámide describen la “altura” del testing en términos de granularidad. Esta sección describe la otra dimensión: las facetas del producto que cada test puede ejercitar. Un mismo nivel —por ejemplo integration— admite tests funcionales, de seguridad, de performance, de privacidad. Los tipos de testing son ortogonales a los niveles: cada categoría se materializa en uno o más niveles según corresponda.

**4.1 Testing funcional**

**Pregunta:** ¿el sistema hace lo que las historias prometen?

**Niveles:** principalmente unit e integration; E2E para flujos completos

**Anclaje al SDD:** criterios de aceptación de cada historia (capa 2)

El testing funcional es el más obvio y el más extendido. Verifica que el comportamiento observable del sistema corresponde al especificado por las historias. La política es que cada historia con criterios de aceptación verificables tiene al menos un test que ejerce esos criterios; idealmente con un mapeo trazable historia → tests, mantenido en metadatos de los archivos de test mismos. Esta trazabilidad permite auditar la cobertura no solo desde el código sino desde el producto: “esta historia, ¿está realmente probada?”.

**4.2 Testing de aislamiento multi-tenant**

**Pregunta:** ¿algún tenant puede ver, modificar o inferir información de otro tenant?

**Niveles:** principalmente integration; complementado con tests introspectivos sobre el schema de la BD

**Anclaje al SDD:** principio constitucional P1, control de seguridad C4.1, ADR-006

**Severidad de las fallas:** P0 — bloquean release sin excepción

**Suite test_tenant_isolation**

Existe una suite dedicada que crea dos tenants A y B con datos completos en todas las entidades del producto y ejerce todos los endpoints como user de A intentando ver, modificar o eliminar recursos de B. La suite es bloqueante en CI; no se puede mergear con un test de aislamiento rojo. Cuando se introduce un nuevo módulo o tabla con tenant_id, se agrega cobertura específica como parte del PR del módulo (es parte del DoD de la tarea correspondiente del plan, no opcional).

**Tests introspectivos sobre el schema**

Independiente de los tests de comportamiento, hay un test que recorre information_schema de PostgreSQL y verifica que toda tabla con columna tenant_id tiene política RLS activa con nombre tenant_isolation. Este test se ejecuta tras cada migration en CI. Una migración que agrega tabla con tenant_id pero olvida la policy RLS rompe este test específico, lo que hace imposible mergear el cambio sin completar la decisión arquitectónica.

\# tests/security/test_rls_introspection.py

import pytest

TABLES_EXEMPT_FROM_RLS = {

'brands', 'models', 'versions', \# catálogo cross-tenant

'audit_logs', \# política especial

'tenants', 'super_admins', \# tablas administrativas

}

@pytest.mark.asyncio

async def test_every_tenant_table_has_rls_policy(db_session):

tables_with_tenant_id = await db_session.execute(text("""

SELECT table_name FROM information_schema.columns

WHERE column_name = 'tenant_id'

AND table_schema = 'public'

"""))

tables_to_check = {

row\[0\] for row in tables_with_tenant_id

} - TABLES_EXEMPT_FROM_RLS

missing_policies = \[\]

for table in tables_to_check:

policies = await db_session.execute(text("""

SELECT policyname FROM pg_policies

WHERE tablename = :t AND policyname = 'tenant_isolation'

"""), {'t': table})

if not policies.first():

missing_policies.append(table)

assert not missing_policies, (

f'Tablas sin RLS tenant_isolation: {missing_policies}'

)

**4.3 Testing de seguridad**

**Pregunta:** ¿el sistema resiste los escenarios de amenaza identificados en el plan de seguridad?

**Niveles:** unit, integration, contract; complementado con DAST en staging

**Anclaje:** modelo STRIDE del Plan de Seguridad sección 4, controles C1-C9

**Tests de autorización por rol**

Suite que recorre los endpoints expuestos y verifica que cada rol (super_admin, manager, salesperson, admin_staff) tiene exactamente los permisos que su definición declara: 200 donde corresponde, 403 donde no debería pasar. Detecta endpoints que olvidaron decorador require_role y endpoints donde el rol fue mal asignado. La política es que toda nueva ruta entra a la suite automáticamente mediante introspección del router de FastAPI.

**Tests de auth**

JWT con firma manipulada → 401. JWT expirado → 401. JWT con tenant_id distinto al del usuario → 403 o 404 según corresponda. JWT con role manipulado en payload → 401 (rompe firma). Ausencia de token en endpoints protegidos → 401. Refresh token reutilizado tras rotación → 401.

**Tests de inyección y validación**

Inputs con caracteres SQL clásicos → rechazados o sanitizados. Inputs gigantescos (10MB+) → rechazados antes del parsing. Inputs con campos no declarados en el schema → rechazados con 422. Inputs con tipos incorrectos → rechazados con detalle por campo.

**DAST automatizado**

OWASP ZAP en passive scan ejecutado en staging tras cada deploy. Findings de severidad high bloquean promoción a producción; medium se reportan al equipo y entran al backlog. La integración se hace mediante el pipeline de CD: ZAP arranca con la spec OpenAPI, la usa como guía y captura tráfico de los E2E que se ejecutan en staging.

**4.4 Testing de performance**

**Pregunta:** ¿el sistema responde a tiempo bajo la carga esperada y sostiene la carga prolongada?

**Niveles:** tests dedicados ejecutados periódicamente, no en cada PR

**Herramientas:** k6 o Locust para load testing; pytest-benchmark para microbenchmarks

**Microbenchmarks de funciones críticas**

Funciones que se ejecutan en hot path (resolución de tenant context, validación de JWT, parsing de payloads grandes) tienen benchmarks que detectan regresiones de performance entre versiones. La política es que un cambio que duplica el tiempo de una función crítica requiere justificación explícita en el PR; no es bloqueante en CI pero queda registrado y tracked.

**Load tests**

Escenarios de carga ejecutados semanalmente contra staging con datos sintéticos representativos. Los escenarios cubren: carga normal de un tenant medio (10 usuarios concurrentes, mix realista de operaciones); pico esperado de día de promoción (50 usuarios concurrentes, alta tasa de webhooks de WhatsApp); operación bajo degradación parcial (con BD a 80% CPU, ¿el sistema sigue respondiendo o cae?). Los thresholds de aprobación están declarados (p95 latencia \<300ms en endpoints típicos, \<2s en endpoints de búsqueda compleja, error rate \<0.1%).

**Stress y soak tests**

Stress test: subir carga progresivamente hasta encontrar el punto de quiebre del sistema, documentar en qué carga aparece la degradación y qué componente cede primero. Se ejecuta una vez por trimestre o tras cambios significativos de arquitectura. Soak test: mantener carga sostenida durante 24 horas para detectar memory leaks, growth no acotado de logs, exhaustion de connections del pool. Se ejecuta una vez por semestre o tras cambios significativos en componentes con estado.

**4.5 Testing de resiliencia**

**Pregunta:** ¿el sistema degrada elegantemente cuando sus dependencias fallan?

**Niveles:** integration con stubs configurables; chaos testing en staging

**Anclaje:** principio constitucional P7 (resiliencia y degradación elegante), controles C8.x del Plan de Seguridad

**Tests con stubs que fallan a propósito**

Stubs configurables de WhatsApp Cloud API y portal deRuedas que pueden inducir fallas: timeout, 500, 429 rate limit, respuestas malformadas. Tests que ejercen el sistema bajo cada modo de falla y verifican el comportamiento esperado: el endpoint que dependía del proveedor degrada elegantemente (mensaje al user, no error 500), el circuit breaker se abre tras N fallas consecutivas, los reintentos respetan el backoff configurado, los eventos van a DLQ correctamente, las métricas de errores externos se incrementan.

**Chaos testing en staging**

Inyecciones controladas de fallas en el ambiente de staging: matar un container del backend, latencia agregada a la BD, packet loss en la red interna, exhaustion artificial del pool de conexiones. La frecuencia es mensual, programada y anunciada al equipo. Los hallazgos —puntos donde el sistema no se recuperó como se esperaba— van al backlog con prioridad alta. Esta práctica se introduce a partir de la Ola 2 cuando hay equipo y disciplina suficientes; en Ola 1 se reemplaza por tabletop exercises descritos en el Plan de Seguridad.

**4.6 Testing de privacidad y manejo de PII**

**Pregunta:** ¿hay datos personales escapando por logs, exports, mensajes de error o trazas?

**Niveles:** tests específicos sobre el output de logging y de exports

**Anclaje:** Plan de Seguridad sección 6, principio S6 privacidad por diseño

**Tests de sanitización de logs**

Tests que ejercen escenarios donde el sistema logguearía bajo error (fallas de validación con payloads que contienen DNI, teléfonos, emails) y verifican que el output del logger no contiene los datos sensibles en claro: están enmascarados, hasheados o reemplazados por placeholders. La suite recorre los logs producidos durante toda la suite de integration y aplica regex contra patrones de DNI argentino, formatos de teléfono y emails: cualquier coincidencia es falla.

**Tests del derecho de supresión**

Test del endpoint /api/v1/contacts/{id}/forget: tras ejecutarlo, el contacto está anonimizado, sus mensajes asociados están eliminados, su rastro en audit_logs declara la operación pero no incluye los datos personales del titular, el contacto no aparece en exports posteriores ni en búsquedas. Test que recorre todas las tablas del tenant verificando que no quedan referencias identificables al contacto eliminado.

**Tests de exports de datos**

Cuando el tenant exporta datos para portabilidad, el archivo resultante contiene exactamente lo que la política declara (categorías de datos del propio tenant) y nada más (no datos cross-tenant, no datos internos de la plataforma, no metadatos sensibles del sistema). Tests que generan export y comparan estructura y contenido contra el schema esperado.

**4.7 Testing de accesibilidad**

**Pregunta:** ¿los frontends son utilizables por personas con discapacidad?

**Niveles:** tests automatizados con axe-core; sesiones manuales periódicas

**Estándar de referencia:** WCAG 2.1 nivel AA

Los frontends se testean automáticamente con axe-core integrado en los E2E de Playwright. Findings de severidad serious bloquean release; moderate se reportan al backlog. Sesiones manuales con teclado solamente y con lector de pantalla se ejecutan trimestralmente: navegar el producto sin mouse, completar tareas críticas con NVDA o VoiceOver, verificar que los anuncios al cambiar de página son razonables. La política de accesibilidad no es solo cumplimiento normativo: es valor para usuarios reales que enfrentan barreras.

**4.8 Testing de compatibilidad**

Browsers soportados: últimas dos versiones major de Chrome, Firefox, Safari, Edge en desktop; Safari iOS y Chrome Android en mobile. Browsers no soportados: IE de cualquier versión, Opera Mini. La política se publica en el manual de usuario. Los E2E de Playwright se ejecutan contra Chrome y Firefox; tests específicos de Safari se ejecutan semanalmente en pipeline programado dado el costo mayor del entorno macOS.

**4.9 Testing de regresión**

La regresión no es un tipo distinto de testing sino el efecto acumulado de mantener verde toda la suite a lo largo del tiempo. La política es: cuando se descubre un bug en producción, antes de arreglarlo se escribe un test que reproduce el bug; el fix vuelve verde el test. Esto garantiza que el bug no se reintroduce silenciosamente. La suite de regresión crece orgánicamente con la historia del producto y el costo de mantenerla refleja el costo histórico de los bugs.

**4.10 Mapping de tipos a niveles**

|  |  |  |  |  |
|:---|:---|:---|:---|:---|
| **Tipo** | **Unit** | **Integration** | **E2E** | **Otros niveles** |
| Funcional | Sí (lógica) | Sí (endpoints) | Sí (flujos) | — |
| Aislamiento multi-tenant | Limitado | Sí (principal) | Sí (selectivo) | Introspectivo schema |
| Seguridad | Sí (validación) | Sí (auth/autz) | Limitado | DAST en staging |
| Performance | Microbenchmark | — | Limitado | Load/stress/soak dedicados |
| Resiliencia | — | Sí (con stubs) | — | Chaos testing |
| Privacidad | Sí (sanitización) | Sí (exports) | — | Auditoría manual |
| Accesibilidad | — | — | Sí (axe-core) | Sesiones manuales |
| Compatibilidad | — | — | Sí (multi-browser) | — |

**5. Gestión de datos de prueba**

Esta sección cubre cómo se generan, mantienen y usan los datos que alimentan los tests. Es un aspecto que muchas estrategias de QA subestiman pero que tiene impacto desproporcionado: datos de prueba mal diseñados producen tests frágiles, falsos positivos, regresiones inexplicables y, en el peor caso, fugas de datos productivos al ambiente de tests.

**5.1 Política central — datos sintéticos por defecto**

Los datos de prueba en cualquier ambiente del programa son sintéticos. Un dump anonimizado de la base productiva no es aceptable como dato de prueba: la anonimización es difícil de hacer correctamente, suele dejar correlaciones que permiten re-identificación, y crea hábitos de manejo de datos productivos que erosionan la disciplina del equipo. La regla es estricta: ningún dato productivo aparece en ningún ambiente de testing, ni siquiera anonimizado, ni siquiera “por un momento para reproducir el bug”. La excepción es el procedimiento documentado de soporte que permite acceso JIT a datos productivos en producción para reproducir un caso específico, jamás copiándolos a otro ambiente.

**5.2 Factories y fixtures**

Los datos de prueba se construyen mediante factories (factory-boy en Python, fishery o equivalente en TypeScript) que producen instancias de las entidades del dominio con valores por defecto realistas y permiten override de campos específicos por test. Las factories están en módulo dedicado tests/factories y son la única forma admitida de crear entidades en tests: prohibido el código que crea entidades manualmente fuera de factories porque produce duplicación y dificulta mantener consistencia cuando la entidad evoluciona.

\# tests/factories/leads.py

import factory

from faker import Faker

from leads.models import Lead, LeadStatus

fake = Faker('es_AR')

class LeadFactory(factory.Factory):

class Meta:

model = Lead

id = factory.Sequence(lambda n: f'lead-{n:06d}')

tenant_id = factory.SelfAttribute('contact.tenant_id')

contact = factory.SubFactory('tests.factories.ContactFactory')

vehicle_interest = factory.SubFactory('tests.factories.VehicleFactory')

status = LeadStatus.NEW

estimated_value = factory.LazyFunction(

lambda: fake.pyint(min_value=5_000_000, max_value=30_000_000)

)

notes = factory.Faker('paragraph', locale='es_AR')

created_at = factory.LazyFunction(datetime.utcnow)

\# Uso en un test:

lead = LeadFactory(status=LeadStatus.QUALIFIED, estimated_value=15_000_000)

**5.3 Datos sembrados (seeds) por ambiente**

Cada ambiente tiene un set de datos sembrados al inicializarse, ejecutado por scripts versionados en el repositorio. El seed produce un universo testeable: dos o tres tenants ficticios con nombres reconocibles (“Agencia Norte”, “Automotores del Sur”), usuarios por rol en cada tenant con credenciales conocidas internamente, catálogo de marcas y modelos completo, vehículos en distintos estados, leads en distintas etapas del pipeline, conversaciones de WhatsApp con histórico realista. El seed es idempotente: ejecutarlo dos veces produce el mismo estado. Esto facilita demostraciones, reproducción de bugs y onboarding de nuevos miembros del equipo.

**5.4 Aislamiento entre tests**

La regla de oro de los tests automáticos es que cada test es independiente: su resultado no depende del orden de ejecución ni del estado dejado por otros tests. La política para integration tests es transacciones revertidas: cada test corre dentro de una transacción que se hace rollback al final, lo que produce limpieza completa sin necesidad de truncar tablas. Para tests donde la transacción no es viable (porque el código bajo prueba abre sus propias transacciones) se usan bases de datos efímeras por test (testcontainers crea y destruye una BD por test). El costo de tiempo es real pero la robustez compensa.

**5.5 Datos de E2E**

Los E2E ejecutan flujos completos que incluyen creaciones, modificaciones y eliminaciones. La política de aislamiento aplica también: cada E2E arranca con base limpia (vía endpoint /test/reset disponible solo en ambientes no productivos) y termina sin asumir estado posterior. Excepción: tests que verifican persistencia entre sesiones (login, logout, vuelvo a entrar y mis datos siguen ahí) tienen alcance ampliado pero acotado al test específico.

**5.6 Datos para tests de privacidad**

Los tests que verifican manejo correcto de PII usan factories específicas que generan campos con patrones reconocibles: DNI con prefijo TEST-, teléfonos con prefijo +54 9 9999, emails con dominio test.deruedas.com. Esto permite que los tests post-procesen logs y exports buscando los patrones; cualquier coincidencia indica leak. La técnica funciona porque los datos sintéticos tienen marca distintiva pero estructura realista.

**6. Ambientes y promociones**

Esta sección define los ambientes operativos del proyecto, qué tipo de testing ocurre en cada uno y cómo se promueve un cambio entre ellos. La estrategia de ambientes es deliberadamente conservadora: pocos ambientes bien diferenciados con criterios claros de promoción son más útiles que muchos ambientes ad hoc.

**6.1 Topología de ambientes**

|  |  |  |  |
|:---|:---|:---|:---|
| **Ambiente** | **Propósito** | **Datos** | **Acceso** |
| Local / Dev | Desarrollo individual | Sintéticos vía seeds; aislado por desarrollador | Cada desarrollador, en su máquina |
| CI / Sandbox | Suite automática en cada PR | Sintéticos efímeros (testcontainers) | Solo pipeline; no UI accesible |
| Staging | Validación pre-producción | Sintéticos persistentes; resembrado quincenal | Equipo interno + QA + early adopters bajo invitación |
| Producción | Servicio real a tenants | Datos reales de tenants | Tenants vía URL pública; equipo solo con JIT |

**6.2 Local — el ambiente del desarrollador**

Cada desarrollador (humano o agente de IA actuando vía sesión local) tiene un ambiente completo en su máquina mediante docker-compose: backend, frontend, PostgreSQL, Redis, MinIO simulando S3, Keycloak local. El startup completo toma menos de un minuto desde clonar el repo. Los seeds se ejecutan con un comando (make seed) y producen el universo testeable. Esta inversión en developer experience no es lujo: es lo que vuelve viable el ciclo rápido de “cambiar código → ver resultado → ajustar” que la productividad del proceso requiere.

El testing en local es responsabilidad del desarrollador antes de pushear: pre-commit hooks ejecutan linting, formateo y tests unitarios rápidos. Los tests de integration completos típicamente no se ejecutan localmente por costo de tiempo (10 minutos) pero el desarrollador puede ejecutar subsets por módulo afectado. Si los hooks son saltados (mediante git commit --no-verify), CI los ejecuta de todas formas y bloquea el merge.

**6.3 CI — la suite automática**

CI ejecuta en cada push a cualquier rama y especialmente al abrir PR. Es el guardián que decide si el código puede mergearse. Su composición es la siguiente, todas etapas bloqueantes salvo donde se indique. Linting y formateo: ruff (Python), eslint (TS), Prettier. Verificación de tipos: mypy strict, tsc strict. Unit tests con cobertura mínima declarada. Integration tests con testcontainers efímeros. Contract tests contra la spec OpenAPI. Tests de aislamiento multi-tenant. Tests de RLS introspectivos. SAST: semgrep. SCA: pip-audit, npm audit, Trivy en imágenes. Detección de secretos: gitleaks. Tests de accesibilidad básicos en componentes críticos. Build de imágenes Docker con tag temporal. Si todo pasa, el PR es elegible para merge; aún así requiere aprobación humana de un reviewer distinto del autor.

Los tests E2E completos no se ejecutan en CI de cada PR por costo de tiempo: se ejecutan en el pipeline programado nocturno y en el pipeline de promoción a staging. PRs que afectan flujos cubiertos por E2E pueden disparar la suite E2E selectiva mediante etiqueta en el PR (label e2e:required).

**6.4 Staging — el espejo del producto**

Staging es un ambiente que reproduce la topología de producción con la misma versión de software pero con datos sintéticos. Recibe automaticamente la rama main tras cada merge: deploy continuo a staging es la política. En staging se ejecutan tras cada deploy: suite E2E completa, DAST con OWASP ZAP, smoke tests programados cada hora para detectar regresiones de configuración, escaneos de seguridad sobre la imagen desplegada. Los hallazgos en staging bloquean la promoción a producción.

Staging tiene tres usos adicionales valiosos. Demos a stakeholders y prospects sin riesgo de mostrarles datos productivos. Reproducción de bugs reportados por tenants (con datos sintéticos equivalentes al caso real). Onboarding de tenants early adopter en sus primeras horas, antes de mover sus datos a producción. La política es no mezclar usos: los datos del onboarding de un early adopter no se mantienen indefinidamente; al promover el tenant a producción, su staging se limpia.

**6.5 Producción**

La promoción a producción es la única que requiere intervención humana explícita: no hay deploy continuo a producción. La razón es que producción atiende a tenants reales y cualquier incidente tiene impacto comercial inmediato. La promoción ocurre tras una checklist documentada que incluye verificar suite E2E verde en staging, métricas estables durante al menos 24 horas, ausencia de incidentes activos, y aprobación del responsable de release de la semana. Las ventanas de release típicas son a primera hora de día hábil para minimizar impacto en agencias trabajando en horario comercial.

**6.6 Feature flags como mecanismo de release seguro**

La estrategia de release adoptada combina branch trunk-based con feature flags: el código de funcionalidades nuevas se mergea a main aunque la funcionalidad no sea visible al usuario, controlado por flag desactivado por default. Esto permite que los cambios estén en producción siendo verificados por el equipo (con flag activado para usuarios internos) antes de exponerlos al universo de tenants. La alternativa de mantener ramas long-lived hasta que la feature esté “lista” produce merges grandes, conflictos y regresiones difíciles de aislar.

Los flags son temporales por default: se eliminan junto con el código viejo una vez que la nueva feature está estable y adoptada universalmente. Los flags que llevan más de seis meses sin cambio son un anti-patrón que se revisa trimestralmente. Para experimentación A/B prolongada se usan flags marcados explícitamente como persistentes.

**6.7 Promociones formales — checklist**

|  |  |
|:---|:---|
| **Promoción** | **Criterios para proceder** |
| Local → CI (push de PR) | Pre-commit hooks pasados; el desarrollador acepta esperar el feedback de CI. |
| CI → Mergeable a main | Todos los checks bloqueantes verdes; al menos un approver distinto del autor; conversaciones del PR resueltas; rama actualizada con main. |
| Main → Staging (auto) | El deploy es automático tras merge. Smoke tests post-deploy verifican salud. |
| Staging → Pre-prod ready | Suite E2E nocturna verde durante al menos un ciclo; DAST sin findings críticos; métricas estables 24h; ningún incidente activo. |
| Pre-prod ready → Producción | Aprobación humana del responsable de release; ventana de release horaria respetada; canary opcional con porcentaje creciente; rollback plan listo. |

**7. Automatización y pipelines**

Esta sección detalla la implementación concreta de la automatización: pipelines en CI, herramientas, tiempos objetivo y métricas. La política central, derivada del principio Q4, es que toda verificación que pueda automatizarse debe estar en pipeline; las verificaciones manuales son excepción justificada.

**7.1 Estructura de pipelines**

El proyecto opera con cuatro pipelines diferenciados que cumplen funciones distintas y se ejecutan en momentos distintos.

|  |  |  |
|:---|:---|:---|
| **Pipeline** | **Trigger** | **Composición** |
| pr-validation | Push a rama de PR | Linting, type checking, unit tests, integration tests, contract tests, RLS tests, SAST, SCA, secrets scan, build image. |
| main-deploy-staging | Merge a main | Build & push imagen, terraform apply, deploy a staging, smoke tests, anuncio a Slack. |
| nightly | Cron 2:00 AM | Suite E2E completa multi-browser, DAST en staging, load test ligero, dependency updates check. |
| release-production | Manual con aprobación | Re-validación de pipeline staging, canary deploy con porcentaje creciente, smoke tests post-deploy, monitoreo intensivo 30 minutos. |

**7.2 Tiempos objetivo**

La velocidad del feedback es crítica para la productividad del equipo. Los tiempos objetivo son los siguientes.

|  |  |  |
|:---|:---|:---|
| **Etapa** | **Objetivo** | **Justificación** |
| Pre-commit hooks (local) | \<10 segundos | Si tarda más, el desarrollador los saltea. |
| pr-validation completo | \<15 minutos | Permite ciclos de PR de máximo 30 minutos vuelta-vuelta. |
| main-deploy-staging | \<20 minutos | Deploy continuo viable con esta latencia. |
| Suite E2E completa | \<30 minutos | Permite ejecutar 2 veces por noche y on-demand cuando hace falta. |
| release-production | \<60 minutos | Suficiente para release seguro con monitoreo post-deploy. |

**Política sobre suite lenta:** Cuando el tiempo de un pipeline supera el objetivo, no se acepta como nuevo normal: se trabaja activamente para volver al objetivo. Las técnicas comunes son paralelización, eliminación de tests redundantes, optimización de fixtures, uso de testcontainers reusables. El equipo dedica ciclos a este mantenimiento como parte del trabajo de plataforma, no como tarea de fin de semana de un voluntario.

**7.3 Manejo de tests inestables (flaky tests)**

La política sobre flakiness se desarrolla en el principio Q5 pero tiene implementación operativa concreta. CI ejecuta los tests con detección de flakiness habilitada: cuando un test falla, se reintenta una vez; si pasa en el reintento, se marca como flaky en el reporte (no falla el pipeline pero queda registrado). Métrica trackeada: porcentaje de runs donde al menos un test fue flaky. Cuando un test exhibe flakiness en más del 2% de las ejecuciones se abre ticket de investigación con prioridad alta. Tras dos semanas sin corrección, el test se elimina —no se ignora, se elimina— y se documenta la cobertura perdida con plan de reemplazo.

**7.4 Quality gates declarados**

Los quality gates son los criterios bloqueantes que deben pasar para proceder. La transparencia es importante: el equipo conoce de antemano contra qué se evalúa.

- Cobertura de unit tests no inferior a 70% líneas en código de dominio (excluye infraestructura, generated code, migrations).

- Cobertura de branches no inferior a 60% en módulos críticos (auth, leads, conversaciones, billing futuro).

- Cero findings críticos en SAST, cero secretos detectados, cero vulnerabilidades críticas en dependencias.

- Cero violaciones de aislamiento en suite test_tenant_isolation.

- Tiempo total del pipeline pr-validation menor a 15 minutos al p95.

- Tasa de flakiness en pr-validation menor a 1% en los últimos 30 días.

- Cero regresiones en métricas de p95 latencia respecto al benchmark del último release estable, salvo justificación documentada.

**7.5 Métricas de pipeline reportadas**

Las siguientes métricas se reportan semanalmente en dashboard interno y mensualmente al equipo completo. Tiempo medio del pipeline pr-validation por percentil. Tasa de flakiness por suite y total. Tasa de fallas reales (no flakiness): cuántos PRs son rechazados por CI. Cobertura de código por módulo y total, con tendencia. Tiempo medio entre apertura de PR y merge. Cantidad de releases a producción por semana. MTTR de hotfixes. Estas métricas se usan para identificar dónde invertir esfuerzo de plataforma.

**7.6 Continuous testing más allá de CI**

La automatización no termina en CI. Producción tiene synthetic monitoring: ejecutores externos hacen requests programadas a endpoints críticos cada 5 minutos verificando que la respuesta es la esperada (status code, latencia bajo threshold, contenido razonable). Estos sintéticos detectan caídas o degradaciones antes de que los tenants reales se afecten. Las alertas de sintéticos van directo al on-call con severidad inicial P1 que se ajusta tras triage.

**8. Verificación del trabajo del agente de IA**

Esta sección aborda una problemática propia del proceso SDD aplicado con asistencia de IA: cómo verificar que lo que el agente entrega satisface no solo los tests que él mismo escribió sino el comportamiento esperado por el equipo humano. Es una preocupación legítima porque el agente, al producir código y tests al mismo tiempo, puede caer en el sesgo de validar lo que construyó en lugar de validar contra una expectativa independiente. La estrategia de mitigación se apoya en cuatro mecanismos complementarios.

**8.1 Mecanismo 1 — Definition of Done previo a la ejecución**

Cada tarea del plan de implementación tiene su Definition of Done escrito antes de que el agente empiece a ejecutarla, como parte de la capa 5 del SDD. El DoD enuncia los criterios verificables que deben cumplirse para considerar la tarea terminada: “endpoint X devuelve schema Y”, “migration agrega columna Z con default A”, “suite test_module_X tiene N tests verdes”, “endpoint rechaza request sin tenant context con error 401”. El DoD es contrato anterior; el agente lo recibe como input, no como output. Esto cambia la pregunta del agente de “¿qué tests deberían existir?” a “¿cómo demuestro que cumplo estos criterios?”.

**8.2 Mecanismo 2 — Tests de aceptación independientes del agente**

Para tareas críticas (las marcadas con etiqueta high-criticality en el plan), el equipo humano escribe los tests de aceptación antes de pedir la implementación. El agente recibe los tests existentes como parte del contexto y debe producir código que los haga verdes. La diferencia con el escenario anterior es de granularidad: aquí los tests ya están escritos, el agente debe satisfacerlos. Es una versión disciplinada del TDD donde el ciclo “escribir test → falla → implementar → pasa” se distribuye entre humano (escribe los tests) y agente (implementa).

**8.3 Mecanismo 3 — Code review humano enfocado**

Todo PR producido por el agente recibe revisión humana antes de mergearse. La revisión no se limita a verificar que los tests están verdes (esa es función de CI); se enfoca en preguntas que solo un humano puede responder. ¿Los tests cubren los escenarios que un humano experimentado anticiparía? ¿Hay casos límite obvios que el agente no consideró? ¿La implementación elige caminos coherentes con el resto del producto o introduce variantes ad hoc? ¿Hay simplificaciones que están escondiendo complejidad real? La revisión es de calidad del razonamiento, no solo de calidad del output.

**Checklist de code review para trabajo del agente:** El reviewer humano se pregunta cinco cosas. (1) ¿La solución es coherente con el resto del producto o inventa una variante? (2) ¿Los tests cubren escenarios límite no obvios? (3) ¿Hay manejo razonable de errores y casos degradados? (4) ¿La integración con el cuerpo SDD existente es respetuosa (sigue convenciones, anclajes correctos)? (5) ¿Algún test parece existir solo para inflar cobertura sin verificar nada útil?

**8.4 Mecanismo 4 — Tests de aislamiento y de seguridad bloqueantes**

Las suites más críticas para deRuedas —aislamiento multi-tenant, RLS introspectivo, autorización por rol— son bloqueantes en CI sin excepción. El agente no puede mergear código que rompa estas suites, ni siquiera con justificación: si las suites se rompen, el PR vuelve para corrección. Esto neutraliza el riesgo de que el agente, en su afán de completar la tarea, modifique tests que estaban protegiendo invariantes del producto. Las suites bloqueantes son el último anillo de defensa que opera independiente del razonamiento del agente.

**8.5 Antipatrones específicos a vigilar en trabajo de agente**

- Tests que pasan trivialmente: assert True, ausencia de aserciones reales, mocks que devuelven exactamente lo que el assert verifica.

- Tests con setup gigantesco que esconde lo que efectivamente se prueba; difíciles de mantener.

- Cambios a tests existentes para hacerlos pasar en lugar de cambiar el código bajo prueba.

- Tests que solo verifican el camino feliz; ausencia sistemática de tests de error y de borde.

- Cobertura inflada con tests redundantes que ejercen el mismo camino con datos distintos sin aportar.

- Refactors silenciosos donde el agente, al implementar la tarea X, modifica código adyacente para “limpiar” y rompe contratos existentes.

**8.6 Auditabilidad del trabajo del agente**

Cada PR producido por el agente queda asociado al thread de conversación que lo originó. Esto es valioso a posteriori: cuando aparece un bug en producción atribuible a una tarea del agente, el equipo puede revisar el contexto que el agente recibió, las decisiones que tomó y los puntos donde el reviewer humano podría haber detectado el problema. Esta auditoría retrospectiva, hecha sin culpa, alimenta la mejora del proceso: ajusta plantillas de tareas, refina criterios de DoD, identifica patrones donde la revisión humana debe ser más rigurosa.

**9. Métricas del programa de calidad**

Esta sección consolida las métricas que el programa monitorea. Las métricas se reportan en cadencias distintas según su volatilidad y se usan para distintos fines: algunas son de health del equipo, otras son evidencia para auditoría, otras son input para decisiones de release.

**9.1 Métricas de cobertura**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Uso** |
| Cobertura líneas total | Continua (cada PR) | Quality gate; bloquea si baja del threshold. |
| Cobertura líneas por módulo | Semanal | Identifica módulos descuidados. |
| Cobertura branches en módulos críticos | Continua | Indicador de profundidad del testing. |
| Porcentaje de historias con tests trazables | Mensual | Indicador de calidad de la trazabilidad SDD. |
| Cobertura de E2E sobre flujos críticos declarados | Mensual | Verificación de que la suite E2E cumple su rol. |

**9.2 Métricas de calidad operativa**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Uso** |
| Defect density por release (defectos/KLOC entregadas) | Por release | Tendencia de calidad del producto. |
| Escape rate (defectos descubiertos en producción) | Mensual | Eficacia del programa pre-producción. |
| MTTR de bugs por severidad | Mensual | Tiempo desde reporte a fix en producción. |
| Porcentaje de regresiones cubiertas por test post-fix | Por release | Salud del proceso de aprendizaje del equipo. |
| Cantidad de hotfixes por mes | Mensual | Indicador inverso de estabilidad de releases. |

**9.3 Métricas del proceso de testing**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Uso** |
| Tiempo total pipeline pr-validation p50 / p95 | Continua | Health del pipeline; señal de optimización. |
| Flaky test rate | Continua | Bloquea backsliding del programa. |
| Test count por nivel (unit, integration, E2E) | Mensual | Verifica que la pirámide se mantenga. |
| Tiempo medio PR abierto → merged | Semanal | Velocity del equipo; impacto del testing en flow. |
| Cantidad de PRs rechazados por CI por causa | Mensual | Identifica causas frecuentes de fricción. |

**9.4 Métricas específicas de seguridad y aislamiento**

|  |  |  |
|:---|:---|:---|
| **Métrica** | **Cadencia** | **Uso** |
| Cantidad de findings críticos en SAST/SCA por mes | Mensual | Tendencia de la salud de la base de código. |
| Tiempo medio de remediación de vulnerabilidades | Por hallazgo | SLA del programa. |
| Cantidad de tests de aislamiento ejecutados | Continua | Confirma que la suite crece con el producto. |
| Tasa de violaciones de aislamiento detectadas en CI (objetivo: 0) | Continua | Salud crítica; cualquier violación es incidente. |

**9.5 Reportes consolidados**

Las métricas se consolidan en tres reportes con distintas audiencias. El reporte semanal interno del equipo cubre health del pipeline, flaky tests, PRs en proceso, blockers identificados; tiene formato breve, formato dashboard, no requiere narrativa. El reporte mensual al equipo de dirección cubre tendencias de calidad, escape rate, MTTR, cantidad de incidentes; tiene narrativa breve sobre lo que se aprendió y qué se está cambiando. El reporte trimestral disponible bajo NDA a tenants enterprise consolida los anteriores con énfasis en lo que el cliente puede percibir: SLAs cumplidos, incidentes ocurridos, mejoras introducidas.

**10. Roles y responsabilidades**

Esta sección distribuye explícitamente quién es responsable de qué dentro del programa. Como en otras dimensiones del proceso, la claridad de responsabilidades es lo que evita los huecos por los que se cuelan los defectos.

**10.1 Matriz de responsabilidades**

|  |  |  |  |  |  |
|:---|:---|:---|:---|:---|:---|
| **Actividad** | **Dev** | **Tech Lead** | **QA\*** | **CS** | **Agente IA** |
| Escribir tests para código nuevo | R | C | C | — | R |
| Mantener suite verde | R | A | C | — | C |
| Definir DoD de tareas críticas | C | R | C | — | — |
| Code review de PRs | C | R/A | — | — | — |
| Tests E2E de flujos críticos | C | C | R | C | — |
| Sesiones exploratorias | C | C | R | C | — |
| Triage de bugs reportados | C | A | R | R | — |
| Aprobación de release a producción | — | R | C | C | — |
| Reporte mensual de métricas | — | R | C | — | — |
| Mantenimiento del pipeline | C | R | C | — | — |

**Notación:** R = Responsable (hace), A = Aprueba (decide), C = Consultado (aporta input). El rol QA es opcional en MVP: hasta que exista posición dedicada, sus responsabilidades se distribuyen entre Dev y Tech Lead. CS es Customer Success.

**10.2 El rol del agente de IA en el programa**

El agente de IA tiene responsabilidades acotadas en el programa. Puede escribir tests durante la ejecución de tareas del plan; sus tests pasan por revisión humana como cualquier código nuevo. No tiene autoridad para modificar suites bloqueantes (aislamiento, RLS introspectivo) sin aprobación humana explícita; un PR del agente que toque esas suites recibe scrutiny adicional. No tiene autoridad para aprobar releases ni para decidir excepciones a quality gates: esas son decisiones del Tech Lead. El agente puede sin embargo proponer mejoras al programa —sugerir tests que faltan, identificar redundancias en la suite, proponer optimizaciones de pipeline— y esas propuestas se evalúan en revisión humana.

**10.3 Rotación de responsabilidades**

En equipos pequeños como el de un MVP, la rotación de responsabilidades —especialmente la de revisor de PRs— es importante para evitar que el conocimiento crítico se concentre en una persona. La política operativa es que ningún PR es revisado siempre por la misma persona; los reviewers se asignan automáticamente con criterio de balanceo de carga y diversidad de revisores. El “security reviewer” del que habla el Plan de Seguridad es rol con quórum mínimo de dos personas, no rol unipersonal.

**11. Criterios de release**

Esta sección define las condiciones bajo las cuales un cambio puede mergearse, una rama puede promoverse a staging y, finalmente, un release puede ir a producción. La claridad de criterios reduce la fricción social en momentos de presión: cuando el negocio quiere release rápido, el criterio objetivo arbitra sin convertirse en discusión política.

**11.1 Definition of Done — nivel tarea**

Una tarea del plan de implementación está terminada cuando se cumplen todas las condiciones siguientes. El código satisface los criterios declarados en el DoD específico de la tarea. La rama tiene tests para todo el código nuevo, en los niveles que corresponda según el tipo de cambio. La cobertura del módulo afectado no disminuye. CI está completamente verde sobre la rama. Documentación afectada (READMEs, comentarios de schemas, OpenAPI specs) actualizada en el mismo PR. Code review aprobado por al menos un reviewer distinto del autor. Cambios de schema acompañados por migration aplicable y reversible. Anclaje al cuerpo SDD declarado en la descripción del PR (qué tarea, qué sección de spec, qué historias afecta).

**11.2 Definition of Ready — nivel ola/release**

Una ola está lista para entregar como release cuando se cumplen las condiciones siguientes. Todas las tareas declaradas en la ola están en estado completado y mergeadas. La suite completa de testing está verde en staging durante al menos el ciclo de tests E2E nocturno previo. Los criterios de cierre de cada épica afectada por la ola están verificables (las historias correspondientes funcionan end-to-end). No hay bugs abiertos de severidad S0 o S1. Los tests exploratorios manuales de la ola están ejecutados y los hallazgos están abiertos como tickets con severidad asignada. Documentación del cambio para tenants (release notes, eventuales mensajes en la app) preparada.

**11.3 Quality gates por ambiente**

|  |  |
|:---|:---|
| **Ambiente / acción** | **Quality gates** |
| Merge a main | Pipeline pr-validation completo verde; al menos un approver; rama actualizada; no hay conflictos. |
| Deploy automático a staging | Smoke tests post-deploy verdes; health checks responden; métricas iniciales en rango normal. |
| Pre-prod ready | Suite E2E nocturna verde por al menos 1 ciclo en staging; DAST sin findings críticos; métricas estables 24h en staging; no hay incidentes activos en producción. |
| Release a producción | Aprobación humana del responsable de release de la semana; ventana de release respetada (no fuera de horario salvo hotfix); rollback plan listo; canary plan acordado; al menos un miembro del equipo con guardia activa para 30 minutos post-deploy. |
| Hotfix de emergencia | Solo cuando el costo de esperar excede el riesgo de saltar gates: justificación documentada en ticket; rollback inmediato listo; comunicación a Slack del equipo en tiempo real; postmortem obligatorio dentro de 5 días hábiles. |

**11.4 Release notes y comunicación**

Cada release a producción tiene release notes públicas para tenants (publicadas en el portal del tenant) y release notes técnicas internas (en el repositorio). Las públicas se enfocan en lo que el tenant puede percibir: nuevas funcionalidades, mejoras visibles, fixes de bugs reportados. Las internas incluyen además: cambios de schema, configuraciones modificadas, riesgos identificados, action items post-release. La política es que las release notes se escriben durante el desarrollo, no al final; cada PR significativo aporta su párrafo. Esto evita el escenario común donde nadie recuerda qué cambió cuando llega el momento de comunicar.

**12. Gestión de defectos**

Esta sección define el proceso desde que un defecto se reporta hasta que se cierra: cómo se clasifica, cómo se prioriza, qué SLA aplica según severidad, cómo se documenta el aprendizaje.

**12.1 Taxonomía de severidad de defectos**

|  |  |  |  |
|:---|:---|:---|:---|
| **Sev.** | **Etiqueta** | **Criterio** | **SLA de fix** |
| S0 | Bloqueante crítico | Pérdida de aislamiento entre tenants, exposición de PII, downtime total, corrupción de datos. Requiere hotfix. | \<4 horas a producción |
| S1 | Mayor | Funcionalidad central rota para múltiples tenants; workaround inviable; flujos de venta interrumpidos. | \<24 horas a producción |
| S2 | Significativo | Funcionalidad rota para casos específicos; workaround disponible pero molesto; impacta UX significativamente. | \<1 semana |
| S3 | Menor | Defecto cosmético, edge case raro, mejora de UX. | Backlog priorizado, según ola |
| S4 | Trivial | Typo, mejora menor sin impacto operativo. | Sin SLA; entra cuando convenga |

**12.2 Workflow de un defecto**

REPORTE

· Tenant reporta vía soporte / email / status page

· Equipo interno detecta vía monitoring / sintéticos / sesión exploratoria

· Bug bounty / responsible disclosure (sección Plan Seguridad 11.5)

↓

TRIAGE (max 4 horas hábiles)

↓

· Reproducir el bug en staging

· Asignar severidad

· Asignar dueño

· Comunicar al reportante (acuse de recibo + estimación)

↓

FIX

↓

· Escribir test que reproduce el bug → falla

· Implementar fix → test pasa

· Code review

· Merge → staging

· Validar fix en staging

↓

RELEASE

↓

· S0/S1 → hotfix inmediato

· S2 → en próximo release programado dentro del SLA

· S3/S4 → en release de oportunidad

↓

CIERRE

· Confirmar fix en producción

· Comunicar al reportante

· Si S0/S1: postmortem dentro de 5 días hábiles

· Lessons learned al backlog del programa

**12.3 Reproducción de bugs**

La política es que ningún bug se da por entendido hasta que se reproduce. Esto evita el escenario común donde se aplica un fix basado en hipótesis y el bug reaparece bajo otra forma. La reproducción se hace en staging con datos sintéticos equivalentes al caso real; cuando reproducir requiere datos productivos específicos, se sigue el procedimiento JIT del Plan de Seguridad y la actividad queda en audit_logs.

**12.4 Test antes de fix**

Antes de aplicar el fix, se escribe el test que reproduce el bug; ese test debe fallar inicialmente. El fix vuelve verde el test. Esto garantiza que la regresión no ocurra silenciosamente y que el fix realmente resuelve la causa, no solo el síntoma. La regla aplica incluso a hotfixes de S0; la urgencia no es excusa para saltearla, porque el costo del bug repetido es mayor que el de los 20 minutos extra de escribir el test.

**12.5 Postmortems sin culpa**

Defectos S0 y S1 generan postmortem obligatorio dentro de 5 días hábiles, con la misma estructura definida en el Plan de Seguridad sección 7.8: cronología, causa raíz por método de los 5 porqués, causas contributivas, lo que funcionó bien, action items con dueño y deadline. La cultura es sin culpa: la pregunta es “qué condiciones del sistema permitieron este defecto”, no “quién lo introdujo”. Los postmortems alimentan al programa: ajustan plantillas de tareas, refinan criterios de DoD, identifican gaps de testing, sugieren mejoras a herramientas.

**12.6 Métricas de gestión de defectos**

- Inflow: cantidad de defectos reportados por semana, segmentado por origen (tenant, interno, sintético).

- Outflow: cantidad de defectos cerrados por semana.

- Backlog age: edad media de los defectos abiertos por severidad.

- Cumplimiento de SLA: porcentaje de defectos resueltos dentro del SLA por severidad.

- Reapertura: porcentaje de defectos reabiertos tras cierre (indicador de fixes superficiales).

- Bugs por área: distribución de defectos por módulo del producto, identifica áreas con calidad subóptima.

**13. Roadmap de madurez del programa**

Esta sección declara la evolución prevista del programa. Como en el Plan de Seguridad, los hitos se declaran en horizontes de 0-6, 6-12 y 12-24 meses con resultados verificables que permiten auditar el progreso.

**13.1 Estado al cierre de Ola 0**

El programa tiene en Ola 0 los siguientes elementos vigentes: pirámide de tests definida con cobertura unit objetivo, suite de aislamiento multi-tenant bloqueante, suite de RLS introspectiva, integración de SAST/SCA en pipeline, secrets scanning, cobertura básica de E2E sobre flujos de auth y catálogo, deploy continuo a staging, deploy manual aprobado a producción, ambientes diferenciados, factories y seeds documentados. Hay gaps reconocidos: cobertura de E2E sobre flujos de leads y conversaciones aún incompleta; testing de performance ausente; testing de resiliencia ausente; testing de accesibilidad ausente; sin equipo dedicado de QA.

**13.2 Horizonte 0-6 meses (Ola 1)**

Foco: completar cobertura sobre los flujos críticos del producto y comenzar testing de las dimensiones no funcionales.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| Suite E2E completa sobre los 8 flujos críticos identificados | Pipeline nightly ejecuta los 8 flujos en al menos 2 browsers. |
| Tests de privacidad: sanitización de logs y derechos de titulares | Suite dedicada con cobertura en los tres flujos: derecho de acceso, rectificación, supresión. |
| Microbenchmarks de funciones críticas (auth, tenant context, RLS) | Suite ejecutada en CI con tracking de tendencia. |
| Load testing semanal contra staging con escenarios documentados | Reporte semanal de p50/p95/p99 latencias por endpoint. |
| Tests de resiliencia con stubs configurables para WhatsApp y portal | Cobertura de los modos de falla: timeout, 500, 429, malformed. |
| Sesiones exploratorias quincenales con tenants early adopter | Reporte de hallazgos por sesión, action items en backlog. |
| Dashboard de métricas del programa accesible al equipo | Métricas de cobertura, flakiness, MTTR, escape rate, todas en uno. |
| Tests de accesibilidad con axe-core en suite E2E | Findings de severidad serious bloqueando release. |

**13.3 Horizonte 6-12 meses (Ola 2)**

Foco: maduración del programa, primer rol dedicado de QA, automatización profunda.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| Incorporación de QA engineer dedicado | Persona con rol específico, propietaria del programa. |
| Chaos testing programado mensual en staging | Calendario de inyecciones, reporte de hallazgos cada ejecución. |
| Stress test trimestral con identificación de breaking point | Reporte con escenarios y recomendaciones de capacity planning. |
| Soak testing semestral | Reporte de memory growth, leak detection, stability. |
| Synthetic monitoring en producción (uptime checks externos) | Plataforma activa con alerts integrados al on-call. |
| Mutation testing piloto en módulos críticos | Identifica tests débiles que pasan aunque el código bajo prueba está roto. |
| Programa de UAT estructurado con 5 tenants early adopter | Sesiones mensuales, scorecard de calidad por tenant. |
| Penetration testing externo anual | Reporte de findings, plan de remediación cerrado. |
| Visual regression testing en componentes críticos UI | Screenshots versionados; diffs alertan cambios visuales. |

**13.4 Horizonte 12-24 meses (Ola 3)**

Foco: testing como ventaja diferencial competitiva del producto.

|  |  |
|:---|:---|
| **Hito** | **Resultado verificable** |
| Cobertura E2E sobre 100% de flujos críticos declarados | Mapeo historia → tests verificable; cobertura auditable. |
| Programa de bug bounty público con plataforma comercial | HackerOne / Intigriti activo, SLA público, recompensas. |
| Performance testing como gate obligatorio en CI/CD | PRs con regresión de performance bloqueados automáticamente. |
| Resilience testing automatizado en pipeline (chaos en CI) | Inyecciones rutinarias, no solo programadas. |
| Auditoría externa de calidad complementaria a SOC 2 | Reporte independiente sobre el programa de QA. |
| Cobertura de accesibilidad WCAG 2.1 AA verificada | Reporte de auditoría externa de accesibilidad. |
| Plataforma de feedback continuo de tenants integrada al programa | Bugs y mejoras reportados desde la app, integrados al backlog. |

**13.5 Madurez objetivo en 24 meses**

Al cierre de Ola 3 el programa de calidad es ventaja diferencial del producto, no costo. Las métricas de programa están en niveles que permiten responder cualquier infosec questionnaire sin trabajo adicional. La cobertura de testing en todas sus dimensiones es comparable a la de competidores establecidos. El equipo opera con disciplina suficiente para que la velocidad de desarrollo sea alta sin sacrificar calidad. El producto se vende parcialmente por su reputación de calidad: las agencias eligen deRuedas sabiendo que no se cae cuando lo necesitan.

**14. Anexos**

**14.1 Plantilla de plan de testing por feature**

Antes de implementar una feature significativa (típicamente una historia compleja o una épica entera), se redacta un plan de testing específico que se incluye en el PR inicial. La plantilla es la siguiente.

PLAN DE TESTING — \[nombre de la feature\]

Anclaje SDD:

· Historia(s): \[E#-H#, ...\]

· Spec técnica: \[sección\]

· Tareas del plan: \[T-###, ...\]

Riesgos identificados:

· \[riesgo 1: descripción + impacto\]

· \[riesgo 2: ...\]

Tests planeados por nivel:

· Unit:

\- \[test 1\]

\- \[test 2\]

· Integration:

\- \[test 1\]

· E2E (si aplica):

\- \[test 1\]

Casos límite contemplados:

· \[caso 1\]

· \[caso 2\]

Tests de aislamiento multi-tenant requeridos:

· \[sí/no, qué se cubre\]

Tests de seguridad/privacidad relevantes:

· \[si aplica, qué se cubre\]

Cobertura objetivo del módulo:

· \[%\]

Definition of Done:

· \[criterios verificables, que CI valida\]

**14.2 Checklist de release a producción**

- Pipeline pr-validation verde en main.

- Suite E2E nocturna verde durante el último ciclo en staging.

- DAST sin findings críticos en último escaneo de staging.

- Métricas estables en staging (latencias, errores, recursos) durante 24 horas.

- No hay incidentes activos S0 o S1 en producción.

- Release notes públicas y técnicas escritas y revisadas.

- Migrations aplicables y reversibles verificadas en staging.

- Rollback plan documentado por escrito en el ticket de release.

- Aprobación del responsable de release de la semana.

- Ventana de release respetada (no fuera de horario salvo hotfix).

- Al menos un miembro del equipo con guardia activa para 30 minutos post-deploy.

- Comunicación al canal del equipo: “deploy iniciado”, “deploy completo”, “30min sin incidente”.

**14.3 Glosario**

|  |  |
|:---|:---|
| **Término** | **Definición** |
| axe-core | Librería de testing automatizado de accesibilidad mantenida por Deque Systems. Detecta violaciones de WCAG. |
| Canary deploy | Estrategia de release donde la nueva versión se expone gradualmente a una fracción creciente de usuarios antes del 100%. |
| Chaos testing | Práctica de inyectar fallas controladas en sistemas en producción o staging para verificar resiliencia. |
| Contract test | Test que verifica que un componente respeta el contrato declarado de su API o de los eventos que emite/consume. |
| DAST | Dynamic Application Security Testing. Análisis de seguridad sobre aplicación corriendo, no sobre código fuente. |
| DoD | Definition of Done. Criterios verificables que indican cuándo una tarea o release puede considerarse completada. |
| DoR | Definition of Ready. Criterios verificables que indican cuándo algo está listo para entrar a la siguiente etapa. |
| E2E | End-to-End test. Test que ejercita un flujo completo del usuario atravesando todos los componentes del sistema. |
| Escape rate | Métrica que mide la cantidad de defectos que llegan a producción dividida por la cantidad total de defectos detectados (en cualquier ambiente). |
| Factories | Patrón de generación de datos de prueba mediante objetos que producen instancias con valores por defecto y permiten override. |
| Feature flag | Mecanismo de configuración runtime que activa o desactiva funcionalidades sin requerir nuevo deploy. |
| Fishery / factory-boy | Librerías populares para implementar el patrón de factories en TypeScript y Python respectivamente. |
| Flaky test | Test que falla intermitentemente sin que el código bajo prueba haya cambiado. Su tolerancia debe ser cero. |
| Hotfix | Cambio aplicado a producción de manera urgente fuera del ciclo normal de release, motivado por un defecto crítico. |
| Integration test | Test que verifica la interacción de un componente con servicios reales (BD, broker de eventos, storage), pero no con servicios externos genuinos. |
| JIT access | Just-in-Time access. Modelo donde el acceso a recursos sensibles se otorga puntualmente y no es permanente. |
| k6 / Locust | Herramientas para load testing programable. |
| KLOC | Mil líneas de código. Unidad común para densities (defectos por KLOC, por ejemplo). |
| MTTR | Mean Time To Resolve / Repair. Tiempo medio entre detección de un defecto y su resolución. |
| Mutation testing | Técnica que introduce mutaciones (cambios pequeños) en el código bajo prueba y verifica que algún test detecta cada mutación. Tests débiles se identifican porque la mutación pasa sin disparar fallas. |
| OWASP ZAP | Zed Attack Proxy. Herramienta de DAST popular y gratuita. |
| Pirámide de testing | Modelo de distribución de tests donde la base ancha son los unit tests, capas intermedias son integration y contract, cima estrecha son E2E. |
| Playwright | Framework moderno para tests E2E de aplicaciones web, con soporte multi-browser. |
| RLS | Row-Level Security. Mecanismo de PostgreSQL que filtra filas a nivel de motor según política. |
| Schemathesis | Herramienta de contract testing que valida implementación contra schema OpenAPI. |
| Shift-left | Práctica de mover las verificaciones de calidad lo más temprano posible en el ciclo de desarrollo. |
| Soak test | Test de carga sostenida durante períodos largos (24h+) para detectar memory leaks, growth no acotado, exhaustion. |
| Stress test | Test que sube la carga progresivamente hasta encontrar el breaking point del sistema. |
| Synthetic monitoring | Ejecución programada de requests reales contra producción desde monitores externos para detectar caídas. |
| TDD | Test-Driven Development. Ciclo de desarrollo que escribe tests antes que código y los hace pasar. |
| testcontainers | Librería que orquesta containers efímeros (PG, Redis, MinIO) para integration tests. |
| UAT | User Acceptance Testing. Validación con usuarios reales de que la solución resuelve el problema esperado. |
| Unit test | Test que verifica la lógica de una unidad aislada (función, método, clase) sin tocar infraestructura. |
| Visual regression test | Test que compara screenshots de UI entre versiones para detectar cambios visuales no intencionales. |
| WCAG | Web Content Accessibility Guidelines. Estándar de accesibilidad web del W3C, niveles A, AA, AAA. |

**14.4 Control de versiones del documento**

|  |  |  |  |
|:---|:---|:---|:---|
| **Versión** | **Fecha** | **Autor** | **Cambios** |
| 1.0 | Mayo 2026 | Equipo de calidad deRuedas | Versión inicial. Cubre programa de Olas 0 y 1 con roadmap a Ola 3. |

La próxima revisión está prevista para noviembre de 2026 al cierre de la Ola 1, donde se actualizarán: estado real del programa respecto al roadmap, métricas observadas vs objetivo, ajustes a los thresholds de quality gates según comportamiento del equipo y del producto, lecciones aprendidas de los primeros incidentes y postmortems del producto vivo.
