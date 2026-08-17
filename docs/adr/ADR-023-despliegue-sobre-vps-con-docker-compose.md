# ADR-023 — Despliegue sobre VPS único con Docker Compose

- **Estado**: ✅ **Aceptado**
- **Fecha**: 2026-08-17
- **Decisores**: Diseñador del sistema
- **Supersede**: [`ADR-015`](ADR-015-orquestacion-kubernetes-y-gitops.md) (Kubernetes + ArgoCD)
- **Reabre**: `IN-16` (orquestación), que `ADR-015` había cerrado
- **Escala**: el conflicto de disponibilidad a **Dirección + SRE** — ver §Conflicto declarado con N3
- **Afecta**: `C-01` bloque 9 (16 tareas), `T-008`, regla dura 4 de `CLAUDE.md`, `infra/`

---

## Contexto

`ADR-015` decidió Kubernetes + ArgoCD sobre nube gestionada, con Terraform provisionando cluster, red, **base de datos gestionada**, buckets, registry, DNS y certificados. Ese ADR listaba entre sus contras asumidas dos que resultaron decisivas:

> *"Complejidad operativa desde el día uno […] sobre un proyecto que todavía no tiene un endpoint de dominio en producción."*
> *"Costo base mayor: un cluster gestionado cuesta más que contenedores gestionados, aun ocioso."*

El producto compite contra Excel, cuadernos y WhatsApp. Un cluster gestionado factura todos los meses desde antes del primer cliente, y su operación exige un conjunto de habilidades que el proyecto todavía no necesita ejercer. La decisión de infraestructura se revisa a la luz de eso.

`ADR-015` también registraba, como alternativa descartada, exactamente el camino que este ADR adopta:

> *"Terraform sobre contenedores gestionados, sin Kubernetes. Era la recomendación inicial: menor complejidad operativa para la Ola 0, y adoptar Kubernetes más tarde habría sido aditivo."*

Este ADR no descubre una opción nueva: **elige la que `ADR-015` había evaluado y descartado**, invirtiendo el trade-off entre simplicidad inicial y portabilidad temprana.

## Decisión

**Un VPS único en Hostinger, con Docker Compose como orquestador de producción.** Sin nube gestionada, sin Kubernetes, sin ArgoCD.

### Reparto de responsabilidades

| Pieza | De qué se hace cargo |
|---|---|
| **Docker Compose** | Todas las cargas de trabajo: `backend`, `worker`, `frontend-web`, PostgreSQL, Redis, MinIO, OpenSearch. El mismo archivo del entorno local, con un override de producción. |
| **Reverse proxy** (Caddy o Traefik) | Terminación TLS, certificados automáticos, y **la conmutación azul-verde** entre los dos stacks. |
| **GitHub Actions** | Construir, firmar y publicar imágenes etiquetadas con el SHA del commit. **Nada más.** |
| **Agente en el VPS** | Detectar el tag nuevo y aplicar el despliegue. El VPS *tira*; el pipeline no *empuja*. |

### La propiedad de seguridad de `ADR-015` se conserva

`ADR-015` puso como control explícito que **GitHub Actions no reciba credenciales del cluster**, y descartó `kubectl apply` desde CI justamente por obligar a guardar un `kubeconfig` en los secretos del pipeline.

Ese control **sobrevive al cambio de infraestructura** y se mantiene: GitHub Actions **no recibe acceso SSH al VPS**. Su permiso máximo sigue siendo publicar una imagen y escribir un tag. El despliegue lo inicia el VPS, no el pipeline.

Es la razón por la que se elige un agente que tira en vez de un `ssh` desde el workflow. El `ssh` sería más simple de escribir y **regalaría el único control de seguridad que `ADR-015` defendía con argumentos concretos**. Si se decide invertir esto, debe registrarse como desvío explícito.

### Despliegue azul-verde sin Kubernetes

Dos stacks de Compose conviviendo y un reverse proxy cuyo *upstream* determina cuál recibe tráfico. Las pruebas de humo corren contra el stack nuevo antes de conmutar. Si fallan, el upstream no se mueve y el stack viejo nunca dejó de servir.

Es la misma mecánica que `ADR-015` describía con dos `ReplicaSet` y el selector de un `Service`, y satisface igual el requisito de reversión de `platform/delivery-pipeline`: no hace falta revertir, basta con **no conmutar**.

### Servicios de datos autoalojados

PostgreSQL, Redis, MinIO y OpenSearch corren en el VPS. No hay base gestionada.

Esto **cierra una pregunta abierta** que arrastraba [`ADR-020`](ADR-020-rol-de-conexion-sin-bypass-de-rls.md): la tarea 9.2.c de `C-01` existía para averiguar *si la base gestionada del proveedor permitiría un rol de esquema sin `BYPASSRLS`*. Sobre un PostgreSQL propio la pregunta desaparece — el `initdb` y los roles son nuestros. El aislamiento multi-tenant queda **más firme**, no menos.

A cambio, backup y recuperación dejan de ser una casilla del proveedor y pasan a ser trabajo propio, que hay que configurar **y probar**. Un backup que nunca se restauró no es un backup.

### Secretos: SOPS + age

La regla dura 4 dice hoy *"los secretos viven en AWS Secrets Manager / Google Secret Manager"*. Hostinger no ofrece ninguno de los dos.

**Los secretos se versionan cifrados en el repositorio con SOPS + age.** La clave privada de descifrado vive únicamente en el VPS y nunca se versiona.

Conviene separar qué se cae y qué no:

| | |
|---|---|
| **Constitucional (Art. 3)** — *"nunca secretos en el repositorio"* | **Intacto.** Lo que se versiona es texto cifrado, no un secreto legible. |
| **Elección de gestor** — proviene de `spec-tecnica` §1554 (N1) | **Se reemplaza** por este ADR, que es N1 y actúa en su propio dominio. |

Ventajas: historial auditable por `git`, sin un servicio crítico adicional que operar, y el inventario de qué secretos existen sobrevive a la pérdida del VPS.

## Conflicto declarado con N3 — no se resuelve acá

**Este ADR no puede modificar el SLA, y no lo modifica.**

`ADR-000` resolvió `IN-31` fijando **99.0 / 99.5 / 99.9** por competencia de dominio: la disponibilidad es dominio propio de `plan-sre`, que es **N3 y prevalece sobre N1**. Un ADR es N1. El decisor registrado para esa pregunta (`PA-09`) es **Dirección + SRE**.

Lo que corresponde hacer acá es dejar registrado que **la infraestructura elegida no sostiene los números vigentes**, y escalar:

| Compromiso vigente (N3) | Qué pasa sobre un VPS único |
|---|---|
| **Enterprise 99.9 %** — 43 min de caída al mes, con crédito del 25 % | Sin redundancia, una ventana de mantenimiento del proveedor o un reinicio de kernel consume el presupuesto del mes entero. |
| **DR en región alternativa** — RTO 4 h, RPO 1 h | **No existe región alternativa.** El compromiso es hoy inalcanzable, no ajustado. |
| PostgreSQL primary — RTO 1 h, RPO 5 min | Alcanzable con archivado de WAL **fuera del VPS**, y solo si se prueba la restauración. |
| PostgreSQL **replicas** — RTO 30 min | Presupone réplica. Sobre un nodo único no hay ninguna. |
| Ola 3 — *"multi-región activo con RTO < 30 min"* | Incompatible por diseño con un nodo único. |

**Lo que se pide a Dirección + SRE**: ajustar los SLA publicados a lo que la infraestructura sostiene, o dotar de redundancia antes de ofrecer los planes que prometen lo que no se puede cumplir. Hay planes con **devolución de dinero** escritos contra estos números; el riesgo es contractual, no solo técnico.

Hasta que ese decisor se pronuncie, **el conflicto queda abierto y visible**. Este ADR no lo cierra ni lo esconde.

## Consecuencias

### A favor

- **Costo base drásticamente menor**, que es el punto. Un VPS contra un cluster gestionado más base gestionada más buckets.
- **Una sola tecnología de despliegue**, y es la que el equipo ya usa todos los días en local. Un fallo se diagnostica leyendo `docker compose logs`.
- **La pregunta abierta de `ADR-020` sobre `BYPASSRLS` desaparece**, y el control sobre el `initdb` refuerza el aislamiento multi-tenant.
- **Se conserva el control de seguridad de `ADR-015`**: el pipeline sigue sin credenciales de producción.

### En contra — asumidas explícitamente

- **Punto único de fallo.** No hay redundancia de ninguna clase. Es el origen del conflicto con N3 declarado arriba.
- **Backup, restauración y parcheo del sistema operativo pasan a ser trabajo propio.** Lo que antes era una casilla del proveedor ahora hay que hacerlo y verificarlo.
- **Se pierde la portabilidad entre proveedores** que era el argumento central de `ADR-015`. Mudar más adelante a Kubernetes será una migración, no una extensión.
- **Escalado vertical únicamente.** Crecer es agrandar la máquina, hasta que deje de alcanzar.
- **La deriva vuelve a ser silenciosa.** ArgoCD reportaba divergencia entre el estado declarado y el real; un cambio hecho a mano sobre el VPS ahora no lo detecta nadie.

## Alternativas consideradas

**k3s sobre el VPS.** Kubernetes de un nodo: conserva los manifests y el camino a ArgoCD, de modo que una mudanza futura a un cluster real no exigiría reescribir el despliegue. Descartada porque mantiene la complejidad operativa que `ADR-015` asumió **sin la redundancia que la justificaba** — se paga el costo de aprendizaje y operación para obtener, sobre un nodo único, lo mismo que da Compose.

**Docker Swarm.** Despliegue declarativo y *rolling updates* nativos, mucho más liviano que Kubernetes. Descartada por comunidad en retracción y futuro incierto, y porque no hay skill ni documentación del proyecto que lo cubra: sería la única pieza de la stack sin respaldo.

**`ssh` desde GitHub Actions en vez de un agente que tira.** Bastante más simple de implementar. Descartada porque obliga a guardar una clave de acceso al servidor de producción en los secretos del pipeline, que es precisamente el control que `ADR-015` defendió al descartar `kubectl apply`.

## Notas de implementación

- `docker-compose.yml` sigue siendo el del entorno local. Producción es un **override**, no un archivo paralelo que se desincroniza.
- **Verificar que `gitleaks` y `trufflehog` no interpreten los archivos cifrados de SOPS como filtración**, y que —más importante— **sigan detectando un secreto en claro** que se cuele junto a ellos. Un gate que se apaga para no molestar deja de ser un gate.
- El archivado de WAL de PostgreSQL debe salir **fuera del VPS**. Un backup en el mismo disco que la base no protege del escenario que más importa.
- El despliegue se sigue identificando por el SHA del commit, como exige `platform/delivery-pipeline`. El SHA es el tag de la imagen.
- La restauración desde backup necesita un ejercicio **probado y fechado**, no un procedimiento escrito. Sin eso el RPO es una intención.
- `infra/k8s/` y `infra/terraform/` no se crean.

## Trabajo derivado

Ninguno de estos puntos se ejecuta con este ADR. Se listan para que no queden implícitos:

1. **Reescribir el bloque 9 de `C-01`** — 16 tareas de Terraform, ArgoCD y manifests que ya no aplican.
2. **Corregir la regla dura 4 de `CLAUDE.md`**, que nombra dos gestores de secretos inexistentes en este despliegue.
3. **Actualizar `knowledge-base/08` §Secrets management y `knowledge-base/12`**, que declaran rotación trimestral sobre un gestor del proveedor.
4. **Llevar el conflicto de disponibilidad a Dirección + SRE**, con el detalle de §Conflicto declarado con N3.
5. **Revisar `T-030` y la stack de observabilidad**: `ADR-016` eligió Tempo, y su despliegue estaba pensado sobre Kubernetes.
