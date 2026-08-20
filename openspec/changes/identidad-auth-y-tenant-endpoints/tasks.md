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

- [ ] 1.1 `009` — `super_admins`, sin `tenant_id` y sin RLS (`D-3`). Deja de mentir `EXENTAS_DE_RLS`, que hoy declara exenta una tabla inexistente
- [ ] 1.2 Test: el detector introspectivo no reporta `super_admins`, y **sí** reportaría `users` y `user_branches` si les faltara la política
- [ ] 1.3 `010` — `user_role_enum` con **exactamente 3 valores** (`ADR-017`) + `users` + RLS + `FORCE`. **Sin `password_hash`, sin `mfa_secret`, sin `mfa_enabled`** (`ADR-026`, `D-2`)
- [ ] 1.4 Test: `users.tenant_id` es `NOT NULL` — es la consecuencia práctica de que `super_admin` viva aparte (`D-3`)
- [ ] 1.5 Índice `UNIQUE (tenant_id, lower(email))`: unicidad **por agencia**, insensible a mayúsculas
- [ ] 1.6 Test: el mismo email en dos agencias distintas se acepta; repetido en la misma, se rechaza
- [ ] 1.7 `011` — `user_branches` con **`tenant_id` propio** además de las dos FK (`D-8`), RLS y `FORCE`
- [ ] 1.8 Test: una tabla de unión sin política es el agujero clásico — verificar que la tiene
- [ ] 1.9 Verificar que las tres pasan el lint de DDL destructivo sin necesitar el marcador `# migracion-contract:`

## 2. El espejo local — `modules/users/`

- [ ] 2.1 `models.py`: `User`, `UserBranch`, `SuperAdmin`
- [ ] 2.2 Test de arquitectura: **ninguna de las tres declara un campo de credencial**. Reutiliza el guardián de AST de `test_arquitectura.py`, que ya falla ante `password_hash` — extenderlo a `mfa_secret`
- [ ] 2.3 `schemas.py` con `extra="forbid"` (`D-10` de C-04). **`tenant_id` no se declara** en ninguna entrada
- [ ] 2.4 Test: un body con `tenant_id` se rechaza, y el campo no existe en `model_fields`
- [ ] 2.5 `repository.py` con filtro de soft delete por defecto, igual que `tenancy`
- [ ] 2.6 Test: una persona dada de baja no aparece en el listado ordinario, y sí con `incluir_dadas_de_baja=True`

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

- [ ] 5.1 `GET /api/v1/auth/me` — sin ningún parámetro (`D-4`)
- [ ] 5.2 Test: intentar indicar otra identidad **nunca** devuelve información ajena
- [ ] 5.3 Test: sin token responde falta de autenticación, distinguible de falta de permisos
- [ ] 5.4 Test: la respuesta trae sucursales y cuál es la principal, y no falla con cero sucursales
- [ ] 5.5 `POST /api/v1/auth/logout` — *end-session* en Keycloak, **sin denylist propia** (`D-4`)
- [ ] 5.6 Test que documenta la consecuencia asumida: tras el logout, el access token ya emitido **sigue siendo válido hasta vencer**
- [ ] 5.7 `POST /api/v1/auth/accept-invitation` — **público**, no recibe contraseña (`ADR-026` §4)
- [ ] 5.8 Test: token de invitación inválido o vencido se rechaza y deja el estado en `invited`
- [ ] 5.9 Endpoints de `users`: listar, invitar, ver, actualizar, desactivar, dar de baja, asignar sucursales
- [ ] 5.10 Endpoints de `tenancy`: el router que C-04 no escribió — configuración de la agencia y CRUD de sucursales
- [ ] 5.11 Aplicar `require_permission` transcribiendo **literalmente** las celdas de `ADR-024` §6 para `users`, `branches` y `tenant`
- [ ] 5.12 ⚠️ Escribir `docs/openapi.yaml` **sin los 6 endpoints retirados** por `ADR-026` §3. Si aparecen, C-08 genera un cliente que llama a rutas inexistentes y el error sale recién en runtime

## 6. Aislamiento multi-tenant — `T-027`, quality gate bloqueante

- [ ] 6.1 Test: listar personas en el contexto de una agencia devuelve solo las suyas
- [ ] 6.2 Test: sin contexto, cero filas
- [ ] 6.3 Test: crear una persona atribuida a otra agencia se rechaza — exigir `InsufficientPrivilegeError`, no `Exception` a secas
- [ ] 6.4 Verificar que los tests no son vacíos: contar filas reales en la tabla antes de afirmar que una sesión ve cero
- [ ] 6.5 Test cross-tenant sobre `user_branches`: la tabla de unión aísla igual que las dos que une
- [ ] 6.6 Test: un rol de tenant nunca alcanza el espacio administrativo (`ADR-024` §2)

## 7. Cierre

- [ ] 7.1 Suite completa verde, cobertura ≥ 80 % y **sin decrecer**
- [ ] 7.2 `ruff`, `black` y `mypy --strict app` en 0
- [ ] 7.3 `openspec validate --changes --specs --strict` verde
- [ ] 7.4 Auditar los escenarios de las dos capabilities contra los tests que existen de verdad, y escribir la tabla
- [ ] 7.5 Actualizar el estado de C-05 en `CHANGES.md`
- [ ] 7.6 **GATE 3 se abre**: avisar que C-06, C-08 y C-09 quedan desbloqueados
