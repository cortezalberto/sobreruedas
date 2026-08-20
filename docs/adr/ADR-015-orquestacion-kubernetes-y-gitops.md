# ADR-015 — Orquestación con Kubernetes y despliegue GitOps con ArgoCD

- **Estado**: ⛔ **Superado** por [`ADR-023`](ADR-023-despliegue-sobre-vps-con-docker-compose.md) el 2026-08-17 — el despliegue va a un VPS único con Docker Compose, sin Kubernetes ni ArgoCD. `IN-16` queda reabierta y cerrada de nuevo por `ADR-023`.
- **Estado original**: Aceptado
- **Fecha**: 2026-08-13
- **Decisores**: Tech Lead
- **Resuelve**: `IN-16` (ambas mitades) · `PA-20` (parcial — la mitad de trazas la cierra [`ADR-016`](ADR-016-trazas-distribuidas-tempo.md))
- **Afecta**: `C-01` (T-008), `infra/terraform/`, `infra/k8s/`, `.github/workflows/deploy-staging.yml`

---

## Contexto

`T-008` especifica el despliegue a staging *"mediante Terraform o kubectl **según infra elegida**"*. Esa elección no estaba hecha, y `IN-16` la registraba como bloqueante abierto con dos mitades: si se usa Kubernetes, y si se usa ArgoCD.

### Qué dice cada fuente

| Documento | Nivel ([`ADR-000`](ADR-000-precedencia-documental.md)) | Qué dice sobre orquestación |
|---|---|---|
| `spec-tecnica` | **N1** | **Nada.** No menciona Kubernetes en ninguna sección. |
| `plan-implementacion` §4.1 | N2 | `infra/k8s/  # manifests si aplica` — condicional explícito |
| `plan-sre` | N3 | Nada sobre orquestación |
| `mejoras-y-saas` §201 | N4 | *"Infra y DevOps: Kubernetes + Terraform + ArgoCD"*, sobre AWS o GCP, multi-zona, São Paulo o Santiago |

**La jerarquía de `ADR-000` no resuelve esto**, y no por empate: por **vacío**. El único nivel normativo que podría decidir (N1) guarda silencio, N2 lo deja explícitamente condicional (*"si aplica"*), y el único documento que nombra la stack completa es N4, que no es normativo.

Por eso `IN-16` no se resuelve *aplicando* una regla: requiere una decisión que llene el hueco. Es exactamente el caso de la regla 4 de `ADR-000` — *"lo no escrito no es vinculante; un vacío documental es un riesgo abierto, no una licencia para inferir"*.

## Decisión

**Kubernetes como plataforma de orquestación, con despliegue GitOps mediante ArgoCD.** Terraform provisiona el cluster y la infraestructura de soporte; ArgoCD sincroniza las cargas de trabajo.

### Reparto de responsabilidades

| Herramienta | De qué se hace cargo |
|---|---|
| **Terraform** | Cluster de Kubernetes, red, base de datos gestionada, buckets, registry, DNS, certificados. Todo lo que tiene ciclo de vida propio e independiente de un despliegue. |
| **ArgoCD** | Cargas de trabajo dentro del cluster: `Deployment`, `Service`, `Ingress`, `ConfigMap`, `HorizontalPodAutoscaler`. Todo lo que cambia con cada release. |
| **GitHub Actions** | Construir y firmar imágenes, publicarlas al registry, y **actualizar el tag en el repositorio de manifests**. Nada más. |

La frontera es deliberada: **GitHub Actions no recibe credenciales del cluster**. Su permiso máximo es escribir un tag de imagen en un repositorio git.

### Flujo de despliegue

```
GitHub Actions              Repositorio de manifests           ArgoCD
      │                              │                            │
  build + firma                      │                            │
      │                              │                            │
      ├──> registry (tag = SHA)      │                            │
      │                              │                            │
      └──> commit del tag ──────────>│<───────── sincroniza (pull)─┤
                                     │                            │
                                 estado deseado ──────────> cluster Kubernetes
```

El estado del cluster queda **declarado en git y auditable**. Una reversión es `git revert` del commit de manifests, no un procedimiento manual bajo presión.

### Despliegue azul-verde

Dos `ReplicaSet` conviviendo y un `Service` cuyo selector determina cuál recibe tráfico. Las pruebas de humo posteriores corren contra el pool nuevo antes de conmutar el selector. Si fallan, el selector no se mueve y el pool viejo nunca dejó de servir.

Esto simplifica el requisito de reversión de la capability `platform/delivery-pipeline`: no hace falta "revertir" nada, basta con **no conmutar**.

## Consecuencias

### A favor

- **Superficie de credenciales mínima.** El compromiso del pipeline de CI no da acceso al cluster. Es un control de seguridad real, no una preferencia de estilo.
- **El estado del cluster es auditable.** Qué está corriendo y desde cuándo se responde con `git log`, no inspeccionando el cluster.
- **Deriva detectable.** Si alguien modifica el cluster a mano, ArgoCD marca la divergencia contra el estado declarado. Sin GitOps esa deriva es silenciosa.
- **Portabilidad entre proveedores**, que es el argumento que `mejoras-y-saas` da para elegir esta stack.
- **Coherente con la única intención expresada** en el corpus, aunque provenga de un documento no normativo.

### En contra — asumidas explícitamente

- **Complejidad operativa desde el día uno.** Kubernetes y ArgoCD son dos sistemas más que instalar, operar, actualizar y depurar, sobre un proyecto que todavía no tiene un endpoint de dominio en producción.
- **Curva de aprendizaje.** Un fallo de despliegue ahora exige entender Kubernetes, no solo leer un log de CI.
- **Diagnóstico en dos lugares.** Un despliegue que no llega se investiga en GitHub Actions *y* en ArgoCD. El modelo *pull* desacopla, y desacoplar también significa que el CI en verde ya no prueba que el despliegue ocurrió.
- **Costo base mayor**: un cluster gestionado cuesta más que contenedores gestionados, aun ocioso.

Estas contras se registran porque eran el argumento de la alternativa descartada. Están asumidas, no ignoradas.

## Alternativas consideradas

**Terraform sobre contenedores gestionados, sin Kubernetes.** Era la recomendación inicial: menor complejidad operativa para la Ola 0, y adoptar Kubernetes más tarde habría sido aditivo — se cambia el destino del despliegue, no el pipeline. Descartada por decisión del Tech Lead, que priorizó portabilidad entre proveedores y despliegue declarativo desde el inicio por sobre la simplicidad inicial. Es un trade-off legítimo: evita una migración futura a cambio de complejidad temprana.

**Kubernetes con `kubectl apply` desde GitHub Actions, sin ArgoCD.** Menos piezas móviles y un solo lugar donde mirar cuando algo falla. Descartada por dos razones concretas: obliga a guardar un `kubeconfig` con permisos sobre el cluster en los secretos del CI, y permite deriva silenciosa entre el repositorio y el estado real del cluster.

## Notas de implementación

- `infra/k8s/` deja de ser *"si aplica"* del §4.1 y pasa a contener manifests reales.
- `infra/terraform/staging/` provisiona el **cluster**, no los contenedores de aplicación.
- El despliegue se identifica unívocamente por el SHA del commit, como exige `platform/delivery-pipeline`. El SHA es el tag de la imagen.
- `docker-compose.yml` **no cambia**: el entorno local sigue siendo Docker Compose. Kubernetes empieza en staging. Levantar un cluster local para desarrollar sería complejidad sin contrapartida.
