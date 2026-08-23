# C-05 · Auditoría de escenarios contra los tests que existen

Tarea 7.4. **30 escenarios declarados en las dos capabilities, 30 con test.**

No es una lista de intenciones: cada fila nombra el test que lo prueba, y ese test se corrió. Donde el escenario se cumple por una vía distinta de la que sugiere su redacción, la fila lo dice.

---

## `identity/session` — 9 escenarios

| Escenario | Test | Nota |
|---|---|---|
| Consulta de la propia información | `test_devuelve_lo_que_el_token_no_dice` | |
| Intento de consultar a otra persona | `test_no_hay_forma_de_pedir_la_identidad_de_otro` | Query, path y cabecera; ninguna devuelve al otro |
| Sin token | `test_sin_token_es_401_y_no_403` | 401 `not_authenticated`, distinguible del 403 por código |
| Persona con sucursales asignadas | `test_devuelve_lo_que_el_token_no_dice` | |
| Persona sin sucursales asignadas | `test_no_falla_con_cero_sucursales` | Cero sucursales es el estado **normal** de alguien recién invitado |
| El email cambió en el proveedor | `test_si_el_email_del_token_difiere_gana_el_token` | |
| El cambio no altera lo que es nuestro | `test_corregir_el_email_no_toca_rol_agencia_ni_sucursales` | |
| Cierre de sesión | `test_logout_cierra_la_sesion_en_keycloak_y_no_guarda_nada_local` | |
| El token vigente sobrevive hasta su vencimiento | `test_tras_el_logout_el_access_token_ya_emitido_sigue_valido` | Documenta una **consecuencia asumida** (`D-4`), no un defecto |

## `identity/user-management` — 21 escenarios

| Escenario | Test | Nota |
|---|---|---|
| Alta de una persona | `test_crear_usuario_lo_deja_deshabilitado` | Nace deshabilitada y sin credencial |
| Ningún camino escribe una credencial | `test_ninguna_llamada_lleva_una_contrasenia_de_persona` | Revisa **claves de JSON**, recursivo, sobre todo lo que sale por el cable |
| Invitación enviada | `test_pedir_que_fije_contrasenia_dispara_la_accion_en_keycloak` | |
| Aceptación de la invitación | `test_aceptar_la_invitacion_activa_el_espejo` | |
| Token de invitación inválido o vencido | `test_un_token_vencido_no_activa_nada_y_el_espejo_queda_en_invited` | **Por `ADR-035` no hay token propio**: lo cumple la validación de token que ya existe |
| Falla al crear en el proveedor de identidad | `test_si_keycloak_falla_no_queda_una_persona_invitada_en_la_base` | |
| Email repetido dentro de la agencia | `test_el_mismo_email_repetido_en_la_agencia_se_rechaza` | Índice `ux_users_tenant_email` |
| El mismo email en dos agencias distintas | `test_el_mismo_email_en_dos_agencias_se_acepta` | |
| Persona desactivada | `test_desactivar_suspende_aca_y_tambien_en_keycloak` | |
| Persona dada de baja | `test_dar_de_baja_deshabilita_en_keycloak_y_no_borra` | |
| El email se libera con la baja, y volver reutiliza la identidad | `test_dar_de_baja_libera_el_email_y_reinvitar_rehabilita_la_cuenta` | **Escenario corregido**: decía lo contrario |
| La baja no borra la identidad en el proveedor | `test_deshabilitar_no_borra` | Exige que ninguna llamada use `DELETE` |
| Invitación que supera el cupo | `test_invitar_superando_el_cupo_no_crea_nada_ni_local_ni_en_keycloak` | Además exige que **no se haya llamado** a Keycloak |
| Una baja libera cupo para invitar | `test_desactivar_no_libera_cupo_y_dar_de_baja_si` | Medido contra `starter`, que topea en 2 |
| Asignación a varias sucursales | `test_marcar_otra_principal_desmarca_la_anterior` | |
| Cambio de sucursal principal | `test_marcar_otra_principal_desmarca_la_anterior` | La constraint **rechaza**; el servicio desmarca antes |
| Asignación a una sucursal de otra agencia | `test_asignar_una_sucursal_de_otra_agencia_se_rechaza` | |
| El historial sobrevive a la baja | `test_las_asignaciones_sobreviven_a_la_baja` | Y vuelven con la persona al reincorporarse |
| Listado de personas de una agencia | `test_un_manager_ve_el_padron_entero` · `test_el_padron_no_cruza_agencias` | |
| Consulta sin contexto de agencia | `test_sin_contexto_de_tenant_no_se_ve_una_sola_fila` | La política compara contra `NULL` y no devuelve nada |
| Alta atribuida a otra agencia | `test_crear_una_persona_atribuida_a_OTRA_agencia_se_rechaza` | Exige el texto `row-level security policy`, no un `Exception` cualquiera |

---

## Dos escenarios que se cumplen por otra vía que la que su texto sugiere

**"Token de invitación inválido o vencido"** — el escenario supone un token de invitación propio. [`ADR-035`](../../../../docs/adr/ADR-035-aceptar-la-invitacion-sin-token-propio.md) decidió no emitir ninguno: tener un access token válido de Keycloak ya prueba que la persona aceptó. El escenario se cumple igual —un token vencido da 401 y el espejo queda en `invited`— pero por la validación que ya existía, no por una lógica de expiración nueva. **Ese es el punto de la decisión**, no un atajo.

**"El email no se libera con la baja"** — decía lo contrario de lo que corresponde y se corrigió, con las tres evidencias escritas en el propio escenario. El índice parcial es una decisión del bloque 1 con su razón documentada, `make seed` depende de ese comportamiento, y la reincorporación de un empleado es un caso real.

## Lo que queda fuera de C-05, y por qué

**`super_admins` es legible por el rol de aplicación.** La tabla está exenta de RLS por `ADR-017` y el rol `mitutu` tiene `SELECT` sobre ella. Hoy ningún endpoint la consulta, pero la capa de datos lo permite. Revocarlo es una migración, y **C-09 va a necesitar leer esa tabla**: con qué rol lo hace es una decisión de arquitectura del espacio administrativo, no un ajuste de este change.

**Desasignar una sucursal no existe.** `user_branches` no tiene `deleted_at`, así que quitarle una sucursal a alguien conservando el histórico que `D-7` exige necesita una migración y una decisión sobre qué significa *"ya no trabaja ahí"* contra *"nunca trabajó ahí"*. `asignar_sucursales` agrega y actualiza; no borra.

**El formulario del frontend con sesión real no se verificó.** El contrato de los endpoints se ejercitó de punta a punta con tokens válidos, pero la pantalla requiere entrar por Keycloak, y eso lo hace una persona.
