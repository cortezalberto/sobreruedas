# ADR-028 — Tokens de color del design system, y el "Rojo crítico" que no es rojo

- **Estado**: ✅ **Aceptado**
- **Fecha**: 18 de agosto de 2026
- **Change**: `C-07` (`design-system-y-shell-web`), gobernanza **BAJA** — autonomía completa
- **Cierra**: `IN-44` (contraste del azul institucional) e `IN-45` (colisión entre error y advertencia)
- **Depende de**: [`ADR-000`](ADR-000-precedencia-documental.md) — `brand-book` es **N4, no normativo**

---

## Contexto

`C-07` no puede cablear los tokens de color sin resolver dos ítems que
`CHANGES.md` marca como *"no bloqueantes que igual hay que decidir acá"*. Los
dos se resolvieron **midiendo**, no opinando, y uno de los dos resultó ser lo
contrario de lo que la base de conocimiento suponía.

---

## `IN-44` — No había contradicción

`knowledge-base/15` §165 registra que el brand book se contradice: §5.6 declara
que el azul institucional sobre blanco *"cumple AA"* y §6.4.4 dice que *"cumple
AAA (más de 7:1)"*.

**Medición**: `#1F3864` sobre `#FFFFFF` da **11.62:1**.

Las dos afirmaciones son **verdaderas**. AA (4.5:1) es un **piso**, no un techo;
AAA (7:1) es un piso más alto. Un par que da 11.62:1 los cruza a los dos. No hay
nada que resolver: hay un documento que cita el mínimo exigido y otro que cita
el nivel alcanzado.

> Es el mismo patrón que ya apareció con `pip-audit` en C-01: alguien leyó un
> **piso** como si fuera un **techo**, y lo anotó como contradicción. Vale la
> pena nombrarlo, porque va dos de dos.

**Decisión**: el estándar vinculante del proyecto sigue siendo **WCAG 2.1 AA**,
que es lo que declaran de forma consistente `brand-book`, `spec-tecnica` §6.6 e
`historias-usuario`. Que este par en particular alcance AAA es un dato, no un
compromiso: no se promete AAA en ningún lado y no se va a auditar contra él.

---

## `IN-45` — Sí había un problema, y no era de transcripción

`knowledge-base/15` §53 sospecha que el `#974706` del *"Rojo crítico"* es
*"casi con seguridad un error de transcripción del `.docx` original"*, y pide
verificar contra el archivo de diseño antes de implementar.

**Se verificó contra el `.docx`.** El documento fuente
(`autos/deRuedas-brand-book.docx`) dice, para *Rojo crítico*:

    HEX: #974706    RGB: 151, 71, 6    CMYK: 20, 70, 100, 30

Los tres valores son **internamente consistentes**: `#974706` es exactamente
RGB 151,71,6, y el CMYK decodifica a ese mismo marrón anaranjado. **No hay error
de transcripción.** El brand book especifica deliberadamente un marrón
anaranjado y lo llama "Rojo crítico".

### La medición que importa, y la que primero se hizo mal

El primer intento midió el **contraste WCAG entre el rojo y el amarillo** (1.17:1)
y lo uso como evidencia de que colisionan. **Esa es la métrica equivocada.** El
contraste WCAG mide legibilidad de *texto sobre fondo*; dos colores semánticos no
se apilan uno sobre otro, así que su ratio entre sí no dice nada sobre si se
distinguen.

Lo que separa un color de estado de otro es el **tono**:

| Color | HEX | Tono | Separación del amarillo |
|---|---|---|---|
| Amarillo atención | `#9C5700` | 33° | — |
| **Rojo crítico (brand book)** | `#974706` | **27°** | **7°** |
| Candidato adoptado | `#A4161A` | 358° | **35°** |

**7° de separación de tono es indistinguible**, y con eso el brand book viola su
propia regla de tener un color distinto por estado. El problema es real; la
causa que la KB proponía, no.

### Decisión

Se adopta **`#A4161A`** como token de error.

- **Separación de tono de 35°** contra el amarillo de advertencia.
- **7.75:1 sobre blanco** — cruza AA y también AAA.
- Se mantiene en la familia oscura y saturada del resto de la paleta
  (`#1F3864`, `#375623`, `#5B2D8C`), así que no desentona con la marca.

**Se puede decidir acá y no hace falta escalarlo** porque `brand-book` es **N4**
por [`ADR-000`](ADR-000-precedencia-documental.md): insumo e intención comercial,
explícitamente **no normativo**. La paleta es entrada del design system, no ley
sobre él. Este ADR es el registro que el Principio 5 exige para que la decisión
sea vinculante.

⚠️ **Lo que este ADR NO hace**: cambiar el brand book. El documento fuente es
corpus inmutable. Lo que cambia es el token que usa el producto, y queda dicho
por qué difiere.

### El color nunca es el único canal

Aunque ahora los dos tonos se distingan, el design system **no puede apoyar el
significado solo en el color**: es el criterio 1.4.1 de WCAG, y afecta a quien
tiene daltonismo — que es exactamente el eje rojo/naranja.

Todo estado lleva **icono y texto** además del color. Un `role="alert"` con
fondo ámbar y sin palabra que diga qué pasó no cumple, por más separación de
tono que tenga.

---

## Consecuencias

- Los tokens funcionales quedan: éxito `#375623`, advertencia `#9C5700`, error
  **`#A4161A`**, info-meta `#5B2D8C`.
- La auditoría de contraste de `C-07` se automatiza y corre en CI: verifica AA
  sobre los pares que el producto usa de verdad, y la separación de tono entre
  los colores de estado. Un design system cuyo contraste se revisa a ojo se
  degrada en el primer apuro.
- `knowledge-base/15` §53 queda desactualizada en su diagnóstico —dice
  "error de transcripción"— y se corrige apuntando acá.
