# ADR-021 — El tenant y el rol viajan como claims de primer nivel

- **Estado**: 🟢 **Aceptado** — 16-ago-2026
- **Decisores**: Tech Lead
- **Afecta**: `backend/app/core/auth.py` (C-02, T-013), la configuración del realm en **C-05**, y todo endpoint que derive identidad
- **Naturaleza**: **decisión sin fuente en el corpus.** Ninguno de los 11 documentos dice cómo viaja el tenant ni el rol dentro del token. Se registra como ADR porque el Principio 5 de la constitución exige que las decisiones sean explícitas para ser vinculantes — mismo criterio que [`ADR-013`](ADR-013-variables-de-entorno.md).

---

## Contexto

`ADR-007` delega la autenticación enteramente a Keycloak, y la spec de `platform/identity` exige que de un token válido se deriven **identificador, tenant y rol**. El identificador es `sub`, que es estándar. Los otros dos no lo son: son propios del dominio y alguien tiene que decidir dónde se leen.

Keycloak, por defecto, publica los roles en `realm_access.roles` (y en `resource_access.<client>.roles`). El tenant no tiene lugar por defecto en ningún lado.

Sin esta decisión, `core/auth.py` no se puede escribir.

## Decisión

**El tenant y el rol viajan como claims de primer nivel del access token**, con los nombres `tenant_id` y `role`.

```json
{
  "sub": "…",
  "iss": "https://keycloak/realms/deruedas",
  "aud": "backend",
  "tenant_id": "0f1e…",
  "role": "manager"
}
```

**No se usa `realm_access.roles`**, por dos motivos:

1. **Es una lista.** Un usuario con dos roles obligaría a elegir uno, y esa elección no la puede hacer la capa de identidad: no sabe qué operación se está intentando. Elegir "el primero" o "el de mayor privilegio" son dos reglas de negocio inventadas en el peor lugar posible.
2. **El tenant no es un rol** y no tiene lugar natural en esa estructura. Meterlo ahí lo convertiría en un valor que el catálogo de roles tiene que ignorar a mano.

Un claim plano por concepto se lee de una sola forma, y hace que "el token no lo declara" sea inequívoco — que es lo que permite **rechazar** en vez de suponer.

## Consecuencias

### A favor

- `core/auth.py` lee dos claims y no interpreta ninguna estructura anidada.
- Un token al que le falte cualquiera de los dos se rechaza sin ambigüedad, que es lo que la spec exige.
- Cambiar de proveedor de identidad no obliga a replicar el formato interno de Keycloak.

### En contra — asumidas

- **Hace falta configurar dos mappers en el realm.** No es la configuración por defecto, así que un realm recién creado **no** emite estos claims y todo token se rechaza. Cae en C-05, y hasta entonces esta decisión vive únicamente en el código.
- Un usuario que pertenezca a dos tenants necesitaría dos tokens. Es coherente con `ADR-006` —el tenant acota la sesión entera, no la operación— y hoy no hay ningún caso de uso que lo pida.

## Lo que esta decisión NO decide

**Qué valores puede tomar `role`.** El catálogo es `ADR-017` y depende de la ratificación de `E-001`. `core/auth.py` extrae el rol **sin validarlo** contra ningún catálogo (`design.md` D-9 de C-02); quien lo contrasta es `rbac.py`, en el bloque 6.

La separación es deliberada: si la identidad enumerara los roles, la traba de `E-001` se comería también la autenticación, que no tiene por qué esperar.

## Alternativas consideradas

**Leer los roles de `realm_access.roles` y el tenant de un atributo mapeado.** Formato mixto: una estructura anidada para una cosa y un claim plano para la otra, sin ningún motivo que lo justifique más que seguir el default a medias.

**Un claim compuesto** (`deruedas: { tenant_id, role }`). Agrupa lo propio y evita chocar con claims futuros de Keycloak. Se descartó por poco: un nivel de anidamiento a cambio de nada, y `tenant_id` / `role` no colisionan con ningún claim registrado en IANA.
