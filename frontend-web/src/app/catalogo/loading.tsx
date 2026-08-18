/**
 * Estado de carga de `/planes`.
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
 */
export default function CargandoCatalogo() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Catalogo</h1>

      {/* `aria-busy` en vez de un spinner decorativo: es lo que un lector de
          pantalla anuncia. Las tarjetas grises no le dicen nada a nadie. */}
      <div aria-busy="true" aria-live="polite" className="mt-8 grid gap-4 sm:grid-cols-3">
        <span className="sr-only">Cargando el catalogo de vehiculos</span>

        {[0, 1, 2].map((posicion) => (
          <div key={posicion} className="h-48 animate-pulse rounded-lg border border-slate-200" />
        ))}
      </div>
    </main>
  );
}
