# ADR-027 — Escáneres de seguridad: cerrar la distancia entre lo declarado y lo que corre

- **Estado**: ✅ **ACEPTADO** — ratificado el 2026-08-17
  > **Aprobado el paquete completo**: se agregan `trivy` y el plugin de seguridad de eslint, `pre-commit` entra degradado a conveniencia con el texto corregido, `trufflehog` se descarta con motivo registrado, y `semgrep` se posterga a C-07/C-08 declarando que `ruff-S` cubre el SAST de Python.
- **Fecha**: 2026-08-17
- **Proponente**: Tech Lead
- **Decide**: Tech Lead
- **Governance**: **CRÍTICA** — dominio de seguridad
- **Afecta**: `.github/workflows/ci.yml`, `.github/workflows/deploy-staging.yml`, `CLAUDE.md` / `AGENTS.md` (regla dura 4), `knowledge-base/12`
- **Origen**: hallazgo al trabajar sobre el job `security` para `ADR-026`

---

## Contexto

El corpus pide **cinco** controles de escaneo que hoy no corren. La auditoría empezó por tres y aparecieron dos más.

| Control | Quién lo pide | Nivel | Estado real |
|---|---|---|---|
| **`pre-commit`** | regla dura 4 · `knowledge-base/12` §88 | — | ❌ **no existe el archivo ni los hooks** |
| **`trufflehog`** | regla dura 4 · `plan-seguridad` §1415 | N3 | ❌ no existe |
| **`trivy`** | `plan-seguridad` §1415 y §1687 · `plan-testing` §589 | N3 | ❌ no existe |
| **`semgrep`** | `plan-seguridad` §1415 y §1687 · `plan-testing` §589 | N3 | ❌ no existe |
| **eslint con plugin de seguridad** | `plan-seguridad` §1415 | N3 | ❌ solo `jsx-a11y` |

Por `ADR-000`, `plan-seguridad` es **N3 y prevalece sobre N1 dentro del dominio de seguridad**. No son sugerencias.

Lo que sí corre hoy en el job `security`: `pip-audit`, `npm audit --audit-level=high`, `gitleaks` sobre la historia completa, y `gitleaks` sobre el texto extraído de los documentos OOXML.

---

## Los cinco casos no son el mismo problema

### 1. `trivy` — hueco real, y el más serio de los cinco

**Construimos y firmamos imágenes que nadie escanea.** `deploy-staging.yml` usa `docker/build-push-action@v6` y después `cosign sign` sobre el digest.

**Firmar una imagen sin escanearla es peor que no firmarla.** La firma acredita procedencia, y quien la verifica tiende a leer eso como *"esta imagen fue revisada"*. No lo fue: la imagen base puede arrastrar CVEs críticos que ningún control del pipeline mira — `pip-audit` y `npm audit` miran **nuestras dependencias declaradas**, no el sistema operativo de la imagen ni lo que instale el `Dockerfile` por fuera.

Y es el único de los cinco cuyo hueco llega a **producción**: las otras cuatro son controles sobre el código; esta es la última puerta antes del registry.

> **Propuesta**: agregar `trivy` al workflow de publicación, **entre el build y la firma**. Bloqueante para severidad crítica, siguiendo `plan-seguridad` §1415 literalmente. Escanear después de firmar no serviría: la imagen firmada ya existe.

### 2. `pre-commit` — el defecto es **documental**, no operativo

Tres documentos afirman que existe: la regla dura 4, `knowledge-base/12` §88 y un comentario del propio `ci.yml`:

> *"gitleaks corre tambien en pre-commit (regla dura 4). Se repite aca porque un hook local es una cortesia, no un control."*

Ese comentario contiene la respuesta. **Un hook local es una cortesía**: se saltea con `--no-verify` y no existe en la máquina de quien clona por primera vez. **El control es CI, y CI lo tiene.** Así que la ausencia de pre-commit **no es un agujero de seguridad** — es un documento que describe mal el sistema.

Lo cual no lo vuelve inofensivo: un documento de reglas que afirma un control que no ocurre entrena a leerlo como aspiracional. La próxima afirmación que no se cumpla tampoco se va a notar.

> **Propuesta**: implementarlo igual, porque es barato y sí ahorra vueltas —agarrar un secreto antes de pushear evita reescribir historia—, y **corregir el texto** para que diga lo que hace: pre-commit es conveniencia, CI es el control.

### 3. `trufflehog` — probablemente redundante, y la decisión nunca se registró

`gitleaks` ya corre sobre la historia completa **y** sobre el texto extraído de los `.docx` — un punto ciego que se cerró a mano y que `trufflehog` tampoco cubriría solo.

Lo que `trufflehog` agrega sobre `gitleaks` es la **verificación**: puede probar una credencial encontrada contra la API real para distinguir un secreto vivo de uno rotado. Es un diferencial genuino y también un pasivo: implica **hacer llamadas de red con credenciales encontradas**, desde un runner de CI.

Parece que alguien decidió que `gitleaks` alcanzaba. **Esa decisión no está escrita en ningún lado**, y por el Principio 5 no es vinculante — es exactamente el patrón que `ADR-026` corrigió para `pip-audit`.

> **Propuesta**: **no** agregar `trufflehog`, y **registrar por qué** en este ADR: `gitleaks` con versión fijada, historia completa y extracción OOXML cubre el requisito de detección de secretos; la verificación activa se descarta por el riesgo de exfiltrar credenciales desde el runner. Corregir la regla dura 4 para que nombre solo lo que corre.

### 4. `semgrep` — ya está parcialmente cubierto, y eso hay que decirlo

`plan-seguridad` §1415 lo pide *"bloqueante en CI para findings de severidad high"*. Pero **`ruff` ya corre con el conjunto `S` activo** (`pyproject.toml`), que es bandit portado — las mismas reglas de seguridad para Python. Esta misma sesión, `S608` frenó una construcción de SQL por interpolación en una migración.

Lo que `semgrep` agrega: análisis de flujo **entre archivos** (ruff mira un archivo por vez), reglas propias, y cobertura de **TypeScript**, donde hoy no hay ningún control de seguridad.

> **Propuesta**: declarar que **`ruff` con el conjunto `S` satisface el requisito de SAST para Python**, y postergar `semgrep` a cuando exista código de frontend que valga la pena escanear (C-07 / C-08). Registrar la equivalencia acá para que sea vinculante y no un supuesto.

### 5. eslint con plugin de seguridad — real, y conviene ahora justamente porque no hay código

`frontend-web` tiene `eslint-plugin-jsx-a11y` y ningún control de seguridad. `plan-seguridad` §1415 pide el plugin.

Hoy el frontend está casi vacío: C-07 y C-08 lo construyen. **Agregarlo ahora cuesta una línea; agregarlo después es corregir código ya escrito** — el mismo argumento por el que C-04 creó `max_whatsapp_messages_month` antes de que nadie la usara.

> **Propuesta**: agregar `eslint-plugin-security` al `eslint.config.mjs` ahora.

---

## Resumen de lo que se propone

| Control | Propuesta | Dónde |
|---|---|---|
| `trivy` | ✅ **agregar**, bloqueante en crítica, **entre build y firma** | `deploy-staging.yml` |
| eslint security | ✅ **agregar** ahora, antes de que haya código | `frontend-web/eslint.config.mjs` |
| `pre-commit` | ✅ **agregar** como conveniencia + **corregir el texto** que lo llama control | `.pre-commit-config.yaml`, regla dura 4, `knowledge-base/12` |
| `trufflehog` | ❌ **no agregar** + registrar el porqué + corregir la regla dura 4 | este ADR |
| `semgrep` | ⏸️ **postergar** a C-07/C-08 + registrar que `ruff-S` cubre Python | este ADR |

**Dos se agregan, uno se agrega degradado a conveniencia, uno se descarta con motivo, uno se posterga con fecha.** Ninguno queda como está: hoy los cinco son afirmaciones sin respaldo.

---

## Ejecución — 17-ago-2026

| Control | Hecho | Dónde |
|---|---|---|
| `trivy` | ✅ entre el build y la firma, `CRITICAL` bloqueante, escaneando por **digest** | `deploy-staging.yml` |
| eslint security | ✅ `security.configs.recommended` + dependencia declarada | `eslint.config.mjs`, `package.json` |
| `pre-commit` | ✅ creado — `gitleaks` con la **misma versión fijada** que CI, `ruff`, `black`, higiene | `.pre-commit-config.yaml` |
| `trufflehog` | ✅ descartado y registrado | regla dura 4, `knowledge-base/12` |
| `semgrep` | ✅ pospuesto y registrado | este ADR |

**La decisión no vive en un comentario.** `test_auditoria_de_dependencias.py` suma cuatro casos que verifican sobre el `deploy-staging.yml` real que `trivy` **está entre el build y la firma**, que bloquea (`exit-code: 1`, sin `continue-on-error`) y que escanea **por digest y no por tag**. Verificado por mutación: mover `trivy` después de `cosign sign` pone el test en rojo.

**Cuatro documentos decían lo que no ocurría, y quedaron corregidos**: la regla dura 4 en `CLAUDE.md` y `AGENTS.md`, `knowledge-base/12` §88 y §157, un comentario de `ci.yml` y otro del `design.md` de C-01.

> ⚠️ **A confirmar en la primera corrida**: la versión fijada de `aquasecurity/trivy-action@0.28.0`. Se pinnea por el mismo motivo que `gitleaks` —un escáner en `latest` hace que el mismo commit pase hoy y falle mañana— pero el tag exacto no se pudo verificar sin red. Si el step falla por acción inexistente, es eso y no la configuración.

---

## Lo que este ADR no resuelve

**El patrón, que es más grande que estos cinco.** Tres veces en esta sesión apareció lo mismo: un documento afirma un control que no ocurre (`pip-audit` con su desvío en un comentario, `trufflehog` y `pre-commit` acá, `mfa_secret` del lado del esquema). No hay nada que verifique que las **reglas duras** del proyecto describan el sistema real.

Un test que recorriera las afirmaciones verificables de `CLAUDE.md` —*"X corre en CI"*, *"Y está prohibido"*— sería el mismo tipo de control que `test_arquitectura.py` aplica al código y `test_auditoria_de_dependencias.py` al pipeline. **Queda anotado como trabajo pendiente, no como parte de esta decisión.**
