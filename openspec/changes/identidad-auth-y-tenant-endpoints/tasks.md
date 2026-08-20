# C-05 · Tareas

> ✅ **La traba documental de `E-001` cayó el 20-ago-2026.**
>
> `E-001` nombraba la *"migración inicial de `users`"* entre lo que bloqueaba, y `ADR-017` —que fija los tres valores de `user_role_enum`— estaba aceptado **condicionado** a esa ratificación. **Se ratificó sin cambios al texto propuesto**, así que el catálogo quedó firme en `manager`, `salesperson` y `admin_staff`, y el escenario que preocupaba —quitar un valor del enum, migración destructiva prohibida en un paso por la regla dura 13— **ya no puede ocurrir**.
>
> ⚠️ **Esto NO habilita a empezar.** La puerta de abajo tiene tres hojas y `E-001` era una sola. La **0.2** sigue cerrada: el bloque 6 de C-02 (`core/rbac.py`) está destrabado pero **sin implementar**, y los endpoints de este change lo invocan. **Regla dura 12**: no se implementa sobre un bloqueante sin resolver.

> **Gobernanza CRÍTICA.** Es el dominio de autenticación y autorización completo. Ningún código sin aprobación humana explícita — y que `E-001` ya esté ratificada **no cambia esto en nada**: eran dos exigencias distintas y solo se levantó una.

> **TDD estricto.** Cada tarea de implementación va precedida de su test.

## 0. La puerta

- [x] 0.1 Verificar que `E-001` está **ratificada y registrada** —pasos (c), (d) y (e) del Artículo 8—; si no, **detenerse acá** — ✅ **20-ago-2026**: pasos (c) y (d) completos, enmienda registrada como apéndice *append-only* en la constitución, que pasa a **v1.1**. El paso (e) es la comunicación y **queda pendiente de envío por el usuario**; no frena el código, porque lo que la regla dura 12 exige es que la norma esté resuelta y registrada, y lo está
- [ ] 0.2 Verificar que el bloque 6 de C-02 (`core/rbac.py`) quedó implementado: los endpoints de este change lo invocan — ⛔ **ESTA ES LA PUERTA QUE SIGUE CERRADA.** El bloque 6 está destrabado desde el 20-ago pero **no implementado**: 0 de 21 escenarios de `platform/authorization`
- [x] 0.3 Confirmar que `ADR-017` pasó de *"Aceptado condicionado"* a **Aceptado** y actualizar su encabezado — ✅ **20-ago-2026**: encabezado actualizado a *Aceptado pleno* y levantada la consecuencia condicionada del cuerpo del ADR

## 1. Migraciones

- [x] 1.1 **`013`** y no `009` — ese número lo tomó el catálogo de vehículos (C-14) después de que se escribieran estas tareas. `EXENTAS_DE_RLS` deja de declarar exenta una tabla inexistente
- [x] 1.2 [`test_identidad_migraciones.py`](../../../backend/tests/integration/test_identidad_migraciones.py) — `super_admins` sin `tenant_id` ni RLS; `users` y `user_branches` con política **y `FORCE`**. `FORCE` y no solo `ENABLE`: sin él las políticas no se aplican al dueño de la tabla, `pg_policies` la lista igual y cualquier auditoría la da por buena
- [x] 1.3 **`014`**. Enum de 3 valores verificado contra `pg_enum`. Sin las tres columnas de credencial.
      ⚠️ **`users.id` ES el `sub` de Keycloak**, sin `server_default`. Lo hace posible `D-5` —la invitación crea primero en Keycloak—, y lo hace **necesario** `ADR-024` §4: `verificar_alcance` compara `assigned_user_id` contra el `sub` del token. Con un id propio además del `sub` esa comparación no cerraría nunca, o habría que resolver el espejo en cada petición y `get_current_user` dejaría de salir puro del token.
      ⚠️ **Se crean `avatar_url` y `notification_preferences`**, que la spec no tiene: `ADR-024` §6 define `[perfil]` incluyéndolos, y declarar editable un campo inexistente deja la matriz apuntando a la nada.
- [x] 1.4 Verificado, más el test de que el enum tiene exactamente los tres valores de `ADR-017`
- [x] 1.5 Parcial por `deleted_at`, además: si no lo fuera, el email de quien se fue quedaría tomado para siempre y la reincorporación sería imposible
- [x] 1.6 Los dos casos, más el de mayúsculas (`Ana@` vs `ana@` — sin `lower()` dos filas comparten identidad ante Keycloak, que sí normaliza) y el de que dar de baja libera el email
- [x] 1.7 **`015`**. La redundancia de `tenant_id` se paga con **FKs compuestas** contra `(id, tenant_id)` de las dos puntas: así la fila no puede vincular un usuario de una agencia con una sucursal de otra ni por error de código. Sin eso la columna podría decir cualquier cosa y la política RLS aislaría por un dato inventado
- [x] 1.8 Tiene política y `FORCE`, más el test de que la FK compuesta rechaza el cruce entre agencias y el de una sola sucursal principal por persona
- [x] 1.9 **Las tres pasan, y el lint encontró algo real**: `015` agrega `UNIQUE (id, tenant_id)` sobre `users` y `branches`, que ya tienen datos. En el caso general el gate tiene razón; acá no puede violarse porque `id` es la PK.
      No se usó `migracion-contract` —silencia el **archivo entero**, y `015` crea tablas: un `drop_column` agregado el mes que viene pasaría sin que nadie lo vea—. Se agregó **`# migracion-segura:` por línea**.
      ⚠️ **Y el test del marcador nuevo encontró un agujero en el marcador nuevo**: la primera ventana miraba 3 líneas hacia arriba, así que exentaba también la operación de dos líneas más abajo. Declarar una constraint segura habilitaba de rebote un `drop_column`. Ajustado a la línea propia y la anterior, con un test que lo fija.

## 2. El espejo local — `modules/users/`

- [x] 2.1 [`modules/users/models.py`](../../../backend/app/modules/users/models.py). `User.id` sin `default=uuid4`: es el `sub` de Keycloak y lo trae quien crea la fila — un default invitaría a olvidarse de pasarlo, y el síntoma sería una fila que nunca coincide con ningún token
- [x] 2.2 `mfa_secret` **ya estaba** en el guardián desde el 17-ago. Lo que faltaba es **`mfa_enabled`, y no va ahí**: no es una credencial sino un hecho de Keycloak, y meterlo en una lista llamada "nombres de contraseña" sería mentir sobre por qué está prohibido. Tiene su propio control en [`test_users_modelos.py`](../../../backend/tests/unit/test_users_modelos.py), sobre las columnas reales de las tres tablas, con su contrapeso
- [x] 2.3 `PerfilPropio` y `UsuarioEditarPerfil`. Este último es `[perfil]` de `ADR-024` §6 y **no** trae `role`, `status`, `tenant_id`, `email` ni sucursales
- [ ] 2.4 Pendiente — el endpoint de edición de perfil es del bloque 5.9, y sin él no hay body que rechazar. El schema ya está escrito con `extra="forbid"`
- [x] 2.5 Dos filtros en toda consulta ordinaria: `tenant_id` explícito **y** `deleted_at IS NULL`. `incluir_dadas_de_baja` es por palabra clave: pedir a los muertos tiene que leerse en el sitio de la llamada
- [x] 2.6 [`test_users_repositorio.py`](../../../backend/tests/integration/test_users_repositorio.py), con el contrapeso —si nunca devolviera a las dadas de baja, el primer test pasaría igual con un `WHERE false`— y el de que el listado no cruza agencias

## 3. Sincronización con Keycloak

- [ ] 3.1 `infra/keycloak/realm-deruedas.json` versionado e importado al arrancar (`D-9`)
- [ ] 3.2 Test sobre el JSON: **`Direct Access Grants` desactivado**. Es lo que hace cumplible a `ADR-026` — con ese flujo, usuario y contraseña se cambian por un token y el "nunca manejamos contraseñas" pasa a depender de que a nadie se le ocurra usarlo
- [ ] 3.3 Test sobre el JSON: PKCE obligatorio, los *mappers* de `tenant_id` y `role` como claims planos (`ADR-021`), y la vida de los tokens (15 min / 7 días)
- [ ] 3.4 Cliente de administración de Keycloak: crear usuario, deshabilitar, disparar *required action*
- [ ] 3.5 Test: el cliente **nunca** envía una contraseña en ninguna de sus llamadas
- [ ] 3.6 Implementar la corrección del espejo: si el email del token difiere del local, **gana el token** (`D-1`)
- [ ] 3.7 Test: corregir el email **no** toca rol, agencia ni sucursales

## 4. Servicio de usuarios

- [ ] 4.1 Test: invitar crea primero en Keycloak y después local (`D-5`) — el orden es lo que hace recuperable el fallo parcial
- [ ] 4.2 Test: si Keycloak falla, **no** queda una persona invitada en la base
- [ ] 4.3 Implementar `service.py`: invitar, aceptar, desactivar, dar de baja, asignar sucursales
- [ ] 4.4 Registrar el contador de usuarios: `limites.registrar(Recurso.USERS, contar_usuarios)`. **Sin esta línea `assert_can_add_user` levanta** — C-04 lo dejó fallando cerrado para que el olvido sea imposible de no notar
- [ ] 4.5 Test: invitar superando el cupo del plan se rechaza con **402** y no crea nada, ni local ni en Keycloak
- [ ] 4.6 Test: desactivar **sigue** consumiendo cupo; dar de baja lo libera (`D-6`)
- [ ] 4.7 Test: dar de baja **deshabilita** en Keycloak, no borra
- [ ] 4.8 Test: el email de una persona dada de baja **sigue ocupado** en esa agencia
- [ ] 4.9 Test: a lo sumo una sucursal principal por persona; marcar otra desmarca la anterior
- [ ] 4.10 Test: asignar a una sucursal de otra agencia se rechaza
- [ ] 4.11 Test: las asignaciones sobreviven a la baja (`D-7`)

## 5. Endpoints — necesitan `rbac.py` del bloque 6 de C-02

- [x] 5.1 [`modules/users/router.py`](../../../backend/app/modules/users/router.py). Exige `auth:read_me`, alcance `self` (`ADR-033`). No hace falta `verificar_alcance`: el recurso ES el sujeto por construcción, porque el id con que se busca sale del token
- [x] 5.2 Las tres formas en que alguien lo intentaría: query string, path y cabecera. Ninguna devuelve al otro
- [x] 5.3 401 con código `not_authenticated`, distinguible del 403 por código y no solo por estado
- [x] 5.4 Los dos casos. Cero sucursales es el estado **normal** de alguien recién invitado: devolver 500 ahí convertiría eso en una caída.
      Además: la respuesta no trae ninguna clave de MFA ni de credencial, ni siquiera como `null`
- [ ] 5.5 `POST /api/v1/auth/logout` — *end-session* en Keycloak, **sin denylist propia** (`D-4`)
- [ ] 5.6 Test que documenta la consecuencia asumida: tras el logout, el access token ya emitido **sigue siendo válido hasta vencer**
- [ ] 5.7 `POST /api/v1/auth/accept-invitation` — **público**, no recibe contraseña (`ADR-026` §4)
- [ ] 5.8 Test: token de invitación inválido o vencido se rechaza y deja el estado en `invited`
- [ ] 5.9 Endpoints de `users`: listar, invitar, ver, actualizar, desactivar, dar de baja, asignar sucursales
- [ ] 5.10 Endpoints de `tenancy`: el router que C-04 no escribió — configuración de la agencia y CRUD de sucursales
- [ ] 5.11 Aplicar `require_permission` transcribiendo **literalmente** las celdas de `ADR-024` §6 para `users`, `branches` y `tenant`
- [ ] 5.12 ⚠️ Escribir `docs/openapi.yaml` **sin los 6 endpoints retirados** por `ADR-026` §3. Si aparecen, C-08 genera un cliente que llama a rutas inexistentes y el error sale recién en runtime

## 6. Aislamiento multi-tenant — `T-027`, quality gate bloqueante

- [x] 6.1 En `test_users_repositorio.py`
- [ ] 6.2 Test: sin contexto, cero filas
- [ ] 6.3 Test: crear una persona atribuida a otra agencia se rechaza — exigir `InsufficientPrivilegeError`, no `Exception` a secas
- [x] 6.4 Se cuentan las filas de las dos agencias antes de afirmar que no se alcanzan. Sin esto los tests de aislamiento serían verdes sobre una base vacía
- [x] 6.5 El perfil no lista la sucursal de la otra agencia. Es el agujero clásico: las dos puntas protegidas y el vínculo no
- [ ] 6.6 Test: un rol de tenant nunca alcanza el espacio administrativo (`ADR-024` §2)

## 7. Cierre

- [ ] 7.1 Suite completa verde, cobertura ≥ 80 % y **sin decrecer**
- [ ] 7.2 `ruff`, `black` y `mypy --strict app` en 0
- [ ] 7.3 `openspec validate --changes --specs --strict` verde
- [ ] 7.4 Auditar los escenarios de las dos capabilities contra los tests que existen de verdad, y escribir la tabla
- [ ] 7.5 Actualizar el estado de C-05 en `CHANGES.md`
- [ ] 7.6 **GATE 3 se abre**: avisar que C-06, C-08 y C-09 quedan desbloqueados
