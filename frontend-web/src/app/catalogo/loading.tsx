/**
 * Estado de carga de `/catalogo`.
 *
 * HACE DOS COSAS, Y LA SEGUNDA NO ES OBVIA.
 *
 * 1. Lo evidente: la pagina es `force-dynamic` y sale a buscar los datos en
 *    cada pedido. Sin esto, el navegador se queda con la pantalla anterior
 *    mientras espera.
 *
 * 2. Lo que costo encontrar: **sin este archivo, `error.tsx` no se usa.** Un
 *    `loading.tsx` crea el limite de Suspense que le permite a Next emitir el
 *    shell antes de resolver el segmento. Sin ese limite, un fallo del fetch
 *    revienta en la primera pasada de SSR, antes de que exista el borde de
 *    error, y Next cae a su pagina de error GLOBAL — la de `__next_error__`,
 *    que no muestra nada util.
 *
 *    Verificado con el backend apagado: sin `loading.tsx` la respuesta es la
 *    pagina global; con el, es el `error.tsx` de este segmento.
 *
 * ⚠️ SI ESTE ESQUELETO "SE QUEDA PEGADO", MIRA LA PESTAÑA ANTES QUE EL CODIGO
 * ───────────────────────────────────────────────────────────────────────────
 * El limite de Suspense del punto 2 tiene una consecuencia que ya costo una
 * investigacion entera, asi que queda escrita.
 *
 * Como `/catalogo` no alcanza a resolver sus datos antes del flush del shell,
 * Next emite el boundary PENDIENTE y streamea el contenido despues:
 *
 *   <!--$?--><template id="B:0"></template>   ← este esqueleto
 *   <div hidden id="S:0">…40 marcas…</div>    ← el contenido, ya en el documento
 *   <script>$RC("B:0","S:0")</script>          ← la orden de intercambiarlos
 *
 * React 19 NO hace el swap ahi: encola el boundary en `$RB` y programa el
 * reveal real (`$RV`) con **`requestAnimationFrame`**. Y los navegadores no
 * ejecutan rAF mientras `document.visibilityState === 'hidden'`. En una pestaña
 * que nunca se enfoca —toda pestaña manejada por MCP o automatizacion lo es— el
 * reveal jamas corre y este esqueleto queda para siempre, sin un solo error de
 * consola y con el HTML del servidor perfecto. En un navegador de verdad, en
 * primer plano, la pagina se dibuja bien.
 *
 * El diagnostico, desde la consola de la pestaña sospechosa:
 *
 *   document.visibilityState + ' / ' + (window.$RB && window.$RB.length)
 *
 * `hidden / 2` = el reveal quedo encolado y no es culpa de la app. Confirmalo
 * llamando `$RV($RB)` a mano: el contenido aparece al instante.
 *
 * Corolario para no perder el tiempo: quitar un componente de `page.tsx` puede
 * "arreglarlo" y no significa nada. Aligerar el render hace que la pagina
 * termine antes del flush y deje de streamear — cambia SI streamea, no si
 * renderiza. Por eso `/planes` nunca se vio afectada: sus datos llegan a tiempo
 * y su boundary sale ya completo, sin `$RC` que programar.
 */
import { Esqueleto } from '@/components/ui';

export default function CargandoCatalogo() {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-semibold tracking-tight">Catalogo</h1>

      {/* `aria-busy` en vez de un spinner decorativo: es lo que un lector de
          pantalla anuncia. Las tarjetas grises no le dicen nada a nadie. */}
      <div aria-busy="true" aria-live="polite" className="mt-8 grid gap-4 sm:grid-cols-3">
        <span className="sr-only">Cargando el catalogo de vehiculos</span>

        {[0, 1, 2].map((posicion) => (
          <Esqueleto key={posicion} alto="h-48" />
        ))}
      </div>
    </div>
  );
}
