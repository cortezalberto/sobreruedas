/**
 * Que se ve cuando el backend no responde.
 *
 * POR QUE EXISTE ESTE ARCHIVO. `/planes` es `force-dynamic`: sale a buscar los
 * datos en cada pedido. Si el backend esta caido —y en desarrollo se cae seguido,
 * es un `docker compose stop`— sin esto Next muestra su pantalla de error
 * generica, que en produccion es una pagina en blanco con "Application error".
 *
 * Un prototipo que se muestra en una demo necesita fallar de forma legible: el
 * que lo mira tiene que poder distinguir "el backend no esta" de "la aplicacion
 * esta rota".
 *
 * ⚠️ NO se muestra el mensaje de la excepcion. `ErrorDeApi` incluye la ruta y el
 * codigo, y Next ademas borra los mensajes de error del servidor en produccion
 * justamente para no filtrar detalles de infraestructura. Lo que el usuario
 * necesita es saber que puede hacer, y eso es reintentar.
 */
'use client';

import { useRouter } from 'next/navigation';

export default function ErrorDeCatalogo({ reset }: { error: Error; reset: () => void }) {
  const router = useRouter();

  /**
   * ⚠️ `reset()` SOLO NO ALCANZA, y se comprobó a mano.
   *
   * `reset()` vuelve a renderizar el segmento, pero los datos del servidor
   * siguen siendo los que ya fallaron: el router tiene cacheado ese resultado.
   * Con el backend caido, arreglado y el boton apretado, la pantalla seguia
   * mostrando el error.
   *
   * `router.refresh()` es el que vuelve a pedirle el segmento al servidor.
   * Primero refrescar, despues resetear el borde de error.
   */
  function reintentar(): void {
    router.refresh();
    reset();
  }

  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Catalogo</h1>

      <div
        // `role="alert"` para que un lector de pantalla lo anuncie al aparecer,
        // en vez de dejarlo pasar como texto cualquiera.
        role="alert"
        className="mt-6 rounded-lg border-l-4 border-estado-advertencia bg-neutro-fondo p-4"
      >
        <p className="font-medium text-estado-advertencia">
          No se pudo cargar el catalogo de vehiculos.
        </p>
        <p className="mt-1 text-sm text-neutro-texto">
          El servicio no respondio. Si estas en desarrollo, revisa que el backend este levantado.
        </p>

        <button
          type="button"
          onClick={reintentar}
          className="mt-4 rounded-md border border-neutro-borde bg-white px-3 py-1.5 text-sm font-medium text-marca hover:bg-neutro-fondo"
        >
          Reintentar
        </button>
      </div>
    </main>
  );
}
