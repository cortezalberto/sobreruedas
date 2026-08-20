# ADR-034 — Las transiciones permitidas son el tercer eje del permiso

- **Estado**: ✅ **Aceptado**
- **Fecha**: 20 de agosto de 2026
- **Change**: `C-02` (`core-backend-primitives`), bloque 6 — `T-014`, gobernanza **CRÍTICA**
- **Enmienda**: [`ADR-024`](ADR-024-matriz-rbac-canonica.md) §3 — agrega un eje a la forma del permiso
- **Depende de**: [`ADR-024`](ADR-024-matriz-rbac-canonica.md) · [`ADR-033`](ADR-033-alcance-self-distinto-de-own.md) · [`ADR-031`](ADR-031-dominio-opcional-y-los-seis-estados-del-vehiculo.md)

> **Por qué se decide ahora**: la matriz ya está escrita en `core/rbac.py` y hay
> **una celda declarada más ancha que el ADR**. No es deuda documental: hoy un
> vendedor mueve un vehículo propio a cualquier estado que `RN-ST-05` admita, y
> encadenando dos saltos legales llega a venderlo.

---

## Contexto — una celda que §3 no puede expresar

`ADR-024` §6, tabla de Stock:

| Operación | `manager` | `salesperson` | `admin_staff` |
|---|:--:|:--:|:--:|
| `POST /vehicles/{id}/status` | `all` | **`own`, solo `available`→`reserved`** | — |

§3 define el permiso con **dos** ejes: alcance y conjunto de campos. La celda del
vendedor usa los dos y **uno más**: `own` es alcance, pero *"solo
`available`→`reserved`"* no es ni alcance ni campos. No acota **qué registros**
ni **qué columnas**: acota **qué valores** puede tomar una de ellas.

Al transcribir la matriz (tarea 6.5) esa mitad quedó afuera, anotada en el
código. La consecuencia es concreta y está corriendo:

> Un `salesperson` con un vehículo asignado puede mandarlo al taller
> (`available`→`in_workshop`) o archivarlo (`available`→`archived`) de una sola
> vez, y **venderlo en dos pasos**: reservarlo —que sí le corresponde— y después
> `reserved`→`sold`, que `RN-ST-05` admite y la matriz no le concede. La matriz
> dice que solo puede reservar.

El camino de dos pasos es el que importa: cada salto, por separado, parece
inocente. `RN-ST-05` acota qué transiciones existen, no quién las hace, así que
componer dos permitidas no encuentra ningún control en el medio.

Es lo que `ADR-024` §1 prohíbe expresamente: la definición ejecutable **no puede
divergir** de estas tablas sin un ADR que las enmiende.

---

## Decisión

La forma del permiso de §3 pasa a tener **tres** ejes:

| Eje | Valores | Significado |
|---|---|---|
| **Alcance** | `all` · `own` · `self` · *(ausente)* | Qué registros — §4 y [`ADR-033`](ADR-033-alcance-self-distinto-de-own.md) |
| **Campos** | conjunto, opcional | Qué columnas, en escritura **y** en lectura |
| **Transiciones** | conjunto de pares `(desde, hasta)`, opcional | **Nuevo.** Qué cambios de estado. Si está presente, la operación se limita a esos pares |

La única celda que lo usa hoy es la de arriba: `salesperson` sobre
`vehicles:change_status` declara `{(available, reserved)}`. **Ninguna otra celda
de §6 ni de §7 cambia.**

### Por qué un eje y no una segunda clave de permiso

La alternativa seria era partir la operación en dos claves —`vehicles:reserve`
para el vendedor y `vehicles:change_status` para el gerente— y que el endpoint
eligiera cuál exigir según el estado pedido.

Se descarta porque **haría que el permiso exigido dependa del cuerpo de la
petición**. Hoy toda declaración de acceso se resuelve al arrancar la aplicación
—es lo que la tarea 6.3 fijó y lo que hace que un endpoint mal declarado no
llegue a producción—, y una clave elegida en tiempo de petición reintroduce
exactamente la clase de decisión que ese diseño saca del camino caliente.

El eje, en cambio, compone con lo que ya existe: se evalúa **con el registro en
la mano**, igual que `own`, y en el mismo lugar.

### El rechazo es 403, no 422

Son dos negativas distintas y ya hay precedente en `core/errors.py`:

- **422 `TransicionInvalida`** — `RN-ST-05` dice que ese cambio no existe para
  nadie. `in_preparation`→`sold` no lo hace ni el gerente.
- **403 `TransicionNoPermitida`** — el cambio es legal, y **este rol** no lo hace.
  Se resuelve pidiéndoselo a alguien más.

Devolver 422 acá mandaría al vendedor a pensar que el sistema no permite vender,
cuando lo que pasa es que **él** no vende. El orden de evaluación también
importa: primero el alcance, después la transición por rol, y recién entonces la
máquina de estados. Quien no alcanza el registro no se entera de en qué estado
está.

---

## Consecuencias

### A favor

- La celda queda transcrita **entera**, y `ADR-024` §1 vuelve a ser cierto.
- Se cierra una concesión de más que estaba corriendo.
- El eje es opcional y ausente en 69 de las 70 claves: no agrega ruido donde no
  hace falta, por la misma razón que `campos`.

### En contra — asumidas

- **Un eje más que mantener**, con una sola celda que lo usa. Se asume porque la
  alternativa es que la matriz ejecutable diga algo distinto de la matriz
  escrita, y esa divergencia no se nota hasta que alguien la usa.
- **Los estados viajan como `str`** en el conjunto, no como `EstadoDeVehiculo`:
  `core/` no depende de `modules/`. Un test compara el par declarado contra el
  enum real para que la cadena no envejezca sola.

## Lo que este ADR NO cierra

- **`RN-ST-05` no se toca.** La tabla de transiciones legales sigue siendo del
  dominio; este eje solo acota, dentro de ella, cuáles alcanza cada rol.
- **`RN-ST-06`** (vender exige razón) sigue siendo validación de dominio, no
  permiso.
- Ninguna otra celda gana el eje. Los nueve módulos de §8 siguen denegados.
