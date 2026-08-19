/**
 * La pantalla de una seccion del menu que todavia no tiene funcionalidad.
 *
 * POR QUE EXISTEN ESTAS PANTALLAS
 * ────────────────────────────────
 * `knowledge-base/15` §Navegacion del producto define un menu de nueve items.
 * Seis no tenian pantalla, asi que `seccionesVisibles()` los escondia y la barra
 * mostraba tres. El criterio de entonces esta escrito en `lib/secciones.ts` y
 * sigue siendo bueno: *"un item de menu que lleva a un 404 le enseña al usuario
 * a desconfiar del menu entero"*.
 *
 * Lo que cambia acá NO es ese criterio: es que ahora las rutas existen. La barra
 * ofrece el mapa completo del producto y ningun item da 404. `existe` se
 * mantiene como lo que siempre fue —una afirmacion sobre el sistema de
 * archivos—, y `secciones.test.ts` la cruza contra `src/app` en las dos
 * direcciones para que no pueda mentir.
 *
 * ⚠️ NO SON PANTALLAS FALSAS. Una maqueta con datos inventados es peor que un
 * vacio honesto: en una demo se lee como funcionalidad y despues hay que
 * explicar que no lo era. Cada una dice que le falta y **quien la construye**,
 * con el numero de change de `CHANGES.md`. Eso convierte el hueco en
 * informacion: quien entra sabe si esta esperando trabajo ajeno o propio.
 *
 * Se usa `EstadoVacio` —primitivo 5 del design system— porque es exactamente el
 * caso para el que se diseño: "no hay nada todavia" con una salida. El brand
 * book le pide ademas una ilustracion isometrica, que no existe en el corpus; el
 * hueco queda ahi sin inventar un dibujo, igual que en el primitivo.
 *
 * ES UN SERVER COMPONENT. No tiene estado ni escucha nada: son un titulo y un
 * texto. Que `EstadoVacio` sea cliente no obliga a nada acá — un componente de
 * servidor puede renderizar uno de cliente, al reves es lo que no se puede.
 */
import Link from 'next/link';

import { EstadoVacio } from '@/components/ui';

/** El destino del CTA. Es la unica seccion que hoy tiene datos de verdad. */
const SALIDA = { href: '/catalogo', texto: 'Ver el catálogo' } as const;

export function SeccionEnConstruccion({
  titulo,
  descripcion,
  change,
}: {
  titulo: string;
  /** Que va a hacer la seccion. Se escribe a mano: sale de la KB, no del nombre. */
  descripcion: string;
  /**
   * El change de `CHANGES.md` que la construye, ya formateado —`C-19
   * stock-web-listado-y-detalle`—, o `null` si ninguno la cubre todavia.
   *
   * `null` es informacion, no un olvido: Reportes esta en la KB como epica E10
   * pero ningun change del MVP lo toma. Decirlo es mas util que dejar el renglon
   * en blanco, y evita que alguien busque el change que no existe.
   */
  change: string | null;
}) {
  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-semibold tracking-tight">{titulo}</h1>

      <div className="mt-8">
        <EstadoVacio
          titulo="Esta sección todavía no está construida"
          descripcion={descripcion}
          accion={
            <Link
              href={SALIDA.href}
              className="text-sm font-medium text-marca underline underline-offset-4"
            >
              {SALIDA.texto}
            </Link>
          }
        />
      </div>

      {/* Sin `uppercase`, a diferencia del resto de los pies de pagina: el
          identificador del change es un slug —`stock-web-listado-y-detalle`— y
          en versales se lee peor y deja de ser copiable de un vistazo. El
          tamaño y el tono apagado alcanzan para que no compita con el vacio. */}
      <p className="mt-4 text-center text-xs text-neutro-suave">
        {change === null ? 'Sin change asignado en CHANGES.md' : `La construye ${change}`}
      </p>
    </div>
  );
}
