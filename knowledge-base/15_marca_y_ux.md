# Marca y UX

> Fuente primaria: `deRuedas-brand-book.md` (965 líneas). Complementado con `deRuedas-spec-tecnica.md` §6.6 (accesibilidad y localización) y `deRuedas-manual-usuario.md` (navegación real del producto).
>
> El brand book **remite explícitamente** al "design system técnico del frontend" para los tokens concretos de CSS, espaciado y breakpoints — ese documento **no está en el corpus**. Ver `PA-30`.

## Identidad

| Forma | Uso |
|---|---|
| **deRuedas Gestión** | Forma completa |
| **deRuedas** | Forma corta |
| **dR** | Monograma. **Nunca como texto.** |

**Reglas de escritura del nombre**:
- El `de` va **siempre en minúscula**, incluso al inicio de una oración.
- La `R` de *Ruedas* va en mayúscula, **pegada, sin espacio**.

**Formas incorrectas, explícitamente prohibidas**: `De Ruedas` · `DeRuedas` · `deruedas` (válido solo en URLs) · `DERUEDAS` · `deRuedas®` (no hay registro efectivo) · `De Ruedas Gestión`.

**Pronunciación**: /de.ˈrwe.ðas/ — grave, con el acento en la primera "e" de *Ruedas*.

**Esencia de marca**: *"dejarte vender más sin que tengas que aprender a usar otro software"*.

**Promesa de marca**: *"te damos la herramienta de gestión hecha específicamente para agencias como la tuya, que te entiende sin que tengas que enseñarle, que se aprende rápido, y que te acompaña a medida que tu negocio crece"*.

⚠️ **No hay tagline definido.** El brand book lista "logo + tagline" como elemento estructural del footer, pero el texto del tagline no aparece en ninguna parte del documento. Ver `IN-58`.

## Audiencia de marca

*"Dueño o gerente comercial de una agencia de vehículos argentina, mediana o chica, con entre **1 y 4 vendedores activos** y stock entre **20 y 200 vehículos**."*

⚠️ **No coincide con el ICP del plan GTM** (3-15 vendedores, 40-300 vehículos). Ver `IN-36`. Esto no es un detalle cosmético: define a quién se le habla en cada pieza y cuánta densidad de información tolera la interfaz.

## Paleta de colores

| Nombre | HEX | RGB | Rol |
|---|---|---|---|
| **Azul institucional** | `#1F3864` | 31, 56, 100 | Principal: headers, logo, CTA primario |
| **Azul intermedio** | `#2E75B6` | 46, 117, 182 | Acento: subtítulos, links, estados hover |
| **Verde éxito** | `#375623` | 55, 86, 35 | Confirmaciones |
| **Amarillo atención** | `#9C5700` | 156, 87, 0 | Advertencias |
| **Rojo crítico** | `#974706` ⚠️ | 151, 71, 6 | Errores y acciones destructivas |
| **Violeta meta** | `#5B2D8C` | 91, 45, 140 | Información meta, citas |
| **Dorado destacado** | `#FFD966` | 255, 217, 102 | Premium. Uso < 2 % de la composición |
| Blanco | `#FFFFFF` | — | Fondos primarios |
| Gris claro | `#F5F5F5` | — | Fondos secundarios |
| Gris medio | `#BFBFBF` | — | Bordes y separadores |
| Gris texto | `#808080` | — | Texto secundario |
| Gris oscuro | `#404040` | — | Texto principal |
| Casi negro | `#1A1A1A` | — | Texto enfático |

✅ ~~**`IN-45`**~~ — **CERRADO el 18-ago-2026 por [`ADR-028`](../docs/adr/ADR-028-tokens-de-color-y-el-rojo-que-no-era-rojo.md).** El producto usa **`#A4161A`** como color de error, no el `#974706` de esta tabla.

> **El diagnóstico que había acá era incorrecto, y conviene decir en qué.** Esta nota suponía que el `#974706` era *"casi con seguridad un error de transcripción del `.docx` original"* y pedía verificar contra el archivo de diseño. **Se verificó.** El `.docx` fuente dice, para *Rojo crítico*: `HEX: #974706 · RGB: 151, 71, 6 · CMYK: 20, 70, 100, 30` — los tres valores **coinciden entre sí**. No hubo error de transcripción: el brand book especifica deliberadamente un marrón anaranjado y lo llama rojo.
>
> **El problema sí era real**, pero se medía mal. El primer intento comparó el *contraste WCAG* entre el rojo y el amarillo (1,17:1) — métrica equivocada, porque WCAG mide texto sobre fondo y dos colores de estado nunca se apilan. Lo que los separa es el **tono**: el `#974706` está a **7°** del `#9C5700`, y por eso son indistinguibles. El `#A4161A` adoptado está a **35°** y da 7,75:1 sobre blanco.
>
> Se pudo decidir en C-07 sin escalar porque `brand-book` es **N4** por [`ADR-000`](../docs/adr/ADR-000-precedencia-documental.md): insumo, no norma. **El brand book no se modifica** — es corpus inmutable; lo que cambia es el token del producto.

**Proporciones de uso**: neutros ~60 % · azul institucional 25-30 % · secundarios 5-10 % · dorado < 2 %.

## Tipografía

| Familia | Licencia | Uso |
|---|---|---|
| **Inter** (Rasmus Andersson) | SIL OFL | Digital — principal |
| **Source Serif Pro** | SIL OFL | Impresos formales |
| **JetBrains Mono** | Apache 2.0 | Código y valores técnicos |

### Escala jerárquica digital

| Nivel | Tamaño | Peso | Color |
|---|---|---|---|
| Display | 48 pt | Bold | Azul institucional |
| H1 | 32 pt | Bold | Azul institucional |
| H2 | 24 pt | Bold | Azul intermedio |
| H3 | 20 pt | Semibold | Gris oscuro |
| H4 | 16 pt | Semibold | Azul institucional |
| Cuerpo | 14 pt | Regular | Gris oscuro |
| Cuerpo pequeño | 12 pt | Regular | Gris texto |
| Etiqueta | 11 pt | Medium, mayúsculas | Azul institucional |

**Impresos**: cuerpo base 11 pt. Formularios manuscritos: nunca menos de 10 pt.
**Interlineado**: 1,4-1,6×. **Medida de columna**: 50-75 caracteres.

## Logo

**Composición**: isotipo (rueda estilizada, arcos concéntricos con flecha) + logotipo (tipografía custom "deRuedas").

**Variantes**: principal horizontal · vertical · solo isotipo · solo logotipo · monocromática negra · monocromática blanca.

**Área de respeto**: igual a la altura del isotipo, proporcional.

| Variante | Mínimo en pantalla | Mínimo impreso |
|---|---|---|
| Principal horizontal | 120 px de ancho | 30 mm |
| Vertical | 80 px de ancho | 20 mm |
| Solo isotipo | 32 px de lado | 8 mm |
| Favicon | 16 px | — |

## Componentes UI

| Componente | Especificación |
|---|---|
| Top bar | Fondo blanco, logo a la izquierda, borde inferior gris medio |
| Sidebar | Fondo gris claro; ítem activo con fondo azul institucional y texto blanco |
| Botón primario | Fondo azul institucional, texto blanco |
| Botón secundario | Borde y texto azul institucional, fondo blanco |
| Botón destructivo | Fondo rojo crítico, texto blanco. **Requiere modal de confirmación** |
| Mensaje de éxito | Fondo verde claro derivado, ícono check |
| Mensaje de error | Fondo rojo claro derivado, ícono de alerta |
| Estados vacíos | Ilustración isométrica + CTA |

**Bordes**: esquinas redondeadas de 4-6 px en botones de producto.

**Sistema de íconos**: **Lucide Icons** (licencia ISC), trazo de 2 px.
Tamaños: inline 16 px · estándar 20 px · destacado 24 px · hero 48 px.

**Tratamiento fotográfico**: saturación reducida entre -10 % y -20 %.

⚠️ El brand book **no define breakpoints de grid ni sistema de espaciado en px/rem** — remite al design system técnico del frontend, que no existe en el corpus. El plan de implementación menciona **13 componentes UI primitivos** sin enumerarlos. Ver `PA-30`.

## Tono de voz

Cinco dimensiones de personalidad: **tendiendo a informal** (voseo argentino) · **cercano** · **serio con licencia de humor** · **moderno pero no "tech"** · **accesible**.

### Vocabulario controlado (obligatorio)

| Se dice | **No** se dice |
|---|---|
| contacto / lead | prospect, prospecto |
| vehículo | auto, unidad |
| venta / operación | deal, transacción |
| pipeline / embudo | funnel |
| mensaje / conversación | chat |
| el portal | la plataforma de avisos |
| deRuedas / deRuedas Gestión / la app | la herramienta |
| agencia (comercial: "tu agencia") / tenant (solo técnico) | organización, empresa, cuenta |
| función / funcionalidad | feature (en piezas de cliente) |
| soporte | customer service, atención al cliente |
| primeros pasos / alta | onboarding (en piezas comerciales) |

> Nota de coherencia: la palabra **`tenant`** está permitida solo en contexto técnico. Esta KB la usa libremente porque es documentación de ingeniería; las piezas de cliente deben decir "agencia".

### Antipatrones prohibidos

- Frases vacías: *"comprometidos con la excelencia"*.
- Marketing inflado: *"revolucionar"*, *"unique"*, *"game-changer"*.
- Jerga de Silicon Valley en piezas de cliente.
- Diminutivos infantiles.
- Emojis decorativos en piezas formales.
- Culpar a terceros: *"nuestro proveedor falló"*.
- Genéricos vagos: *"próximamente"*.

## Accesibilidad

**Estándar**: **WCAG 2.1 nivel AA** — consistente en `brand-book`, `spec-tecnica` §6.6 e `historias-usuario` (Definición de Terminado). ✅

| Requisito | Valor |
|---|---|
| Contraste, texto normal | **4,5 : 1** |
| Contraste, texto grande (18 pt, o 14 pt bold) | **3 : 1** |
| Contraste, elementos gráficos | 3 : 1 |
| Navegación por teclado | **Completa en todos los flujos** |
| Etiquetas ARIA | Correctas en todos los componentes interactivos |
| Lectores de pantalla probados | **NVDA, JAWS, VoiceOver** |

**Herramientas de verificación**: WebAIM Contrast Checker (diseño), `axe-core` integrado en Playwright y `jest-axe` (automatizado). En el pipeline, los findings de severidad *serious* **bloquean el release**.

✅ ~~**`IN-44`**~~ — **CERRADO el 18-ago-2026 por [`ADR-028`](../docs/adr/ADR-028-tokens-de-color-y-el-rojo-que-no-era-rojo.md): no había contradicción.**

> §5.6 dice que el azul institucional sobre blanco *"cumple AA"* y §6.4.4 que *"cumple AAA (más de 7:1)"*. **Medido: 11,62:1.** Las dos afirmaciones son verdaderas — AA (4,5:1) es un **piso**, AAA (7:1) es un piso más alto, y ese par los cruza a los dos.
>
> Es la segunda vez que el proyecto anota como contradicción lo que era **un piso leído como techo** — la primera fue el escenario de `pip-audit` en C-01. Vale tenerlo presente al revisar el resto de las inconsistencias.
>
> El estándar vinculante sigue siendo **AA**, que es lo que declaran de forma consistente `brand-book`, `spec-tecnica` §6.6 e `historias-usuario`. Que este par alcance AAA es un dato, no un compromiso.

## Localización

- **Idioma por defecto**: español de Argentina (`es-AR`). Voseo en toda la interfaz.
- **Fechas**: `dd/mm/aaaa`.
- **Números**: separador de miles con punto, decimal con coma.
- **Moneda**: ARS y USD, con formato argentino.
- **Zona horaria por defecto**: `America/Argentina/Buenos_Aires`, configurable por tenant.
- **Validaciones específicas**: CUIT con dígito verificador · dominio en formato `AA999AA` (Mercosur) o `AAA999` (viejo) · DNI.

## Compatibilidad de cliente

| Plataforma | Soporte |
|---|---|
| Navegadores | Últimas 2 versiones mayores de Chrome, Firefox, Safari y Edge |
| iOS | 15 y posteriores |
| Android | API 26 (Android 8.0) y posteriores |
| Resolución desktop | Desde 1280×720 |
| Resolución mobile | Desde 360×640 |

## Navegación del producto

Estructura de menú principal (derivada del manual de usuario):

```
Dashboard                          [G+D]
Stock                              [G+S]
  ├─ Agregar vehículo ⚠️ (las historias dicen "Nuevo vehículo" — IN-47)
  └─ Importar → Descargar plantilla
Leads                              [G+L]
  └─ Nuevo lead
Mensajes                           [G+M]
Reportes                           [G+R]
  ├─ Exportar
  ├─ Exports anteriores
  ├─ Custom            (solo Enterprise)
  └─ Programar
Configuración
  ├─ Usuarios → Agregar usuario
  ├─ Pipeline → Editar
  ├─ Sucursales → Agregar sucursal
  ├─ Reglas de asignación
  ├─ Integraciones
  │   ├─ WhatsApp Business
  │   └─ Portal sectorial
  ├─ WhatsApp → Plantillas / Cambiar número
  ├─ Email → Plantillas
  ├─ Campos personalizados
  ├─ Webhooks          (Pro y Enterprise)
  └─ API → Tokens      (Enterprise ⚠️ IN-25)
```

**Atajos de teclado**: `Ctrl+K` buscador global · `Ctrl+N` crear nuevo · `Ctrl+S` guardar · `Esc` cerrar modal · `?` ayuda contextual · más los `G+letra` de navegación.

**Dashboards diferenciados**: el del vendedor tiene 4 zonas; el ejecutivo del manager, 5.

## Consideración de diseño derivada de la constitución

El Principio 2 (*Simplicidad antes que features*) tiene una consecuencia directa sobre la UI: **el producto compite contra Excel, cuadernos y WhatsApp**, y una agencia que necesita más de 4 horas de capacitación probablemente lo abandone. El manual promete un producto "operativo en menos de 20 minutos".

Esto implica que, ante cualquier duda de diseño, **gana la opción más obvia y lineal**, incluso a costa de flexibilidad. La persona "Carla" (vendedora) tiene **veto de facto** sobre la adopción según el plan GTM: si la interfaz no le sirve en el piso de venta, el producto falla, aunque el dueño haya firmado el contrato.
