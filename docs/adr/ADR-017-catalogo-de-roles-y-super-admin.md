# ADR-017 — Catálogo de roles y representación del Super Admin

- **Estado**: ✅ **Aceptado pleno** — la enmienda [`E-001`](E-001-enmienda-glosario-super-admin.md) quedó **ratificada el 20-ago-2026** y con eso cae la condición. La constitución pasa a **v1.1**
- **Fecha**: 2026-08-13 · condición levantada el 2026-08-20
- **Decisores**: Tech Lead
- **Resuelve**: `IN-01`, `IN-02` · `PA-02` · habilita `R-2` (matriz RBAC)
- **Afecta**: `C-02` (T-014, `core/rbac.py`), `C-05`, migración inicial de `users`
- **Governance**: **CRÍTICO** — `rbac.py` es el mecanismo de autorización del sistema

---

## Contexto

`IN-01` catalogaba cinco versiones incompatibles del catálogo de roles:

| Fuente | Nivel | Catálogo |
|---|---|---|
| `constitucion`, glosario Parte IV | **N0** | **3 roles, en español**: Gerente, Vendedor, Administrativo |
| `spec-tecnica` §3.3 (`user_role_enum`) | N1 | 3 roles, en inglés: `manager`, `salesperson`, `admin_staff` |
| `spec-tecnica` §8.4 | N1 | 3 roles, en español (dentro del mismo documento que usa inglés en el enum) |
| `plan-implementacion` T-014 | N2 | **4 roles**: `super_admin`, `manager`, `salesperson`, `admin_staff` |
| `plan-seguridad`, `plan-testing` | N3 | 4 roles, idéntico al plan |
| `historias-usuario` | N4 | 5 personas (incluye Customer Success Manager) |

`IN-02` agregaba el problema estructural: `spec-tecnica` §4.1.3 y §4.2.11 definen **11 endpoints bajo `/admin/api/v1`** para el Super Admin, pero `users.tenant_id` es `FK NOT NULL` — **el modelo, como está escrito, no puede representarlo.**

## Decisión

### 1. El catálogo del sistema tiene cuatro roles; el enum de usuarios tiene tres

Esta distinción es el núcleo de la decisión, y resuelve lo que parecía una contradicción entre las dos elecciones tomadas.

```
Catálogo de roles del sistema (4)
├── Roles de tenant  → user_role_enum, tabla users
│   ├── manager       ≡ Gerente
│   ├── salesperson   ≡ Vendedor
│   └── admin_staff   ≡ Administrativo
└── Rol de plataforma → tabla super_admins
    └── super_admin
```

`user_role_enum` **conserva sus tres valores**. `super_admin` no es un cuarto valor del enum: es un actor de naturaleza distinta, que vive en su propia tabla. El "catálogo de 4 roles" de T-014 y de los planes de seguridad y testing es correcto como inventario de roles del sistema; lo que no corresponde es meter los cuatro en el mismo enum.

### 2. El Super Admin vive en `super_admins`, fuera de `users`

- `users.tenant_id` **sigue siendo `FK NOT NULL`**, sin excepciones.
- `super_admins` es una tabla propia, sin `tenant_id`, **exenta de RLS**.
- La autenticación sigue delegada a Keycloak (ADR-007), con un rol de realm `super_admin` que discrimina el flujo.
- `audit_logs` referencia al actor con un par `(tipo_de_actor, id)`, de modo que las acciones del Super Admin quedan atribuidas y trazables.

**Evidencia a favor**: `plan-testing` ya menciona `super_admins` en su lista de tablas exentas de RLS. La tabla estaba anticipada por una de las fuentes; nunca se la conectó con el enum.

### 3. Los identificadores en código son en inglés, con equivalencia documentada

`manager` ≡ Gerente, `salesperson` ≡ Vendedor, `admin_staff` ≡ Administrativo. La interfaz de usuario muestra los términos en español del glosario.

**Lectura del glosario**: la Parte IV establece que un término *"se asume con el **significado** aquí establecido"*. Fija significados, no lexemas. Un identificador en inglés cuyo significado es el del glosario **no lo contradice**, siempre que la equivalencia esté documentada. Aun así, la tabla de equivalencia se somete a ratificación en `E-001` para que la lectura no quede implícita — el Principio 5 es explícito en que lo implícito no es vinculante.

## Por qué esto reduce la enmienda necesaria

Al sacar al Super Admin de `users`, **el glosario de la constitución sobrevive intacto**:

| Definición del glosario | ¿La toca esta decisión? |
|---|---|
| *"Un usuario pertenece exactamente a un tenant"* | **No.** Se preserva: `tenant_id` sigue `NOT NULL`. El Super Admin no es un `Usuario` en el sentido del glosario. |
| *"Un usuario tiene un rol (Gerente, Vendedor, Administrativo)"* | **No.** Siguen siendo esos tres. |

La enmienda pasa de ser una **modificación** del glosario —cambiar el catálogo de roles de un usuario, que es lo que el planteo original de `IN-01` sugería— a ser una **adición**: definir el término canónico *"Super Admin"*, que hoy falta.

Una adición que no contradice nada es un trámite de Artículo 8 mucho menos contencioso que una modificación que sí contradice. **La decisión de la tabla aparte no solo es mejor técnicamente: abarata el costo documental.**

## Consecuencias

### A favor

- **El invariante de aislamiento multi-tenant queda sin excepciones.** `users.tenant_id NOT NULL` es la base sobre la que se apoyan las políticas RLS y los tests de aislamiento bloqueantes en CI. Un solo `NULL` permitido obliga a que cada query y cada política contemplen el caso.
- **Es estructuralmente imposible que un Super Admin se filtre en una query de tenant**: no está en la tabla que esas queries recorren.
- **Trazabilidad de auditoría preservada**, a diferencia de representarlo solo como rol de Keycloak.
- **Desbloquea `R-2`** (matriz RBAC) y con ello `C-02`.

### En contra — asumidas

- **Dos caminos de autenticación que mantener**: uno para usuarios de tenant, otro para Super Admins. Es la contrapartida directa de no tocar el invariante.
- **`audit_logs` necesita un actor polimórfico** en lugar de una `FK` simple a `users`. Se define en C-03.
- ~~**La decisión queda condicionada** a que `E-001` se ratifique. Si el equipo la rechaza, este ADR se revisa.~~ — ✅ **Resuelto el 20-ago-2026**: `E-001` fue ratificada sin modificaciones al texto propuesto, así que este ADR queda firme tal como está. No hubo nada que revisar.

## Alternativas consideradas

**`super_admin` como cuarto valor del enum, con `tenant_id` nullable.** Un solo modelo de usuario y un solo flujo de autenticación. Descartada porque rompe `users.tenant_id NOT NULL`, que `12_seguridad_y_compliance.md` califica como el control más crítico del sistema. El costo no es la migración: es que cada query y cada política RLS gana permanentemente un caso nulo que contemplar, y basta con olvidarlo una vez.

**Solo rol de Keycloak, sin fila en base de datos.** Cero cambios en el modelo y máxima coherencia con ADR-007. Descartada porque `audit_logs` no tendría a quién atribuir las acciones del Super Admin, y la trazabilidad de auditoría es requisito de compliance bajo la Ley 25.326.

**Tres roles, respetando el glosario sin enmienda.** Cero fricción documental y `C-02` arrancaría de inmediato. Descartada porque deja huérfanos los 11 endpoints de `/admin/api/v1` que la spec técnica ya define, y porque contradice a T-014, `plan-seguridad` y `plan-testing` simultáneamente.
