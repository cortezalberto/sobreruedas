/**
 * Barra de navegacion.
 *
 * ES UN CLIENT COMPONENT, y por una sola razon: `usePathname`. Marcar cual es la
 * seccion actual necesita saber la ruta, y eso solo existe en el cliente.
 *
 * Es la unica pieza interactiva del arbol; todo lo que cuelga de ella —las
 * paginas— sigue renderizando en el servidor. Poner el `'use client'` en el
 * layout habria arrastrado al cliente todo lo que contiene.
 *
 * QUE SECCIONES MUESTRA — no las decide este archivo
 * ────────────────────────────────────────────────────
 * Salen de `lib/secciones.ts`, que es la fuente unica que comparte con la ayuda
 * de atajos y con el acorde `G`. Antes cada uno tenia su lista y podian derivar:
 * agregar una seccion acá no le agregaba el atajo, y un atajo podia llevar a una
 * ruta que la barra no conocia.
 *
 * `seccionesVisibles()` deja afuera lo que todavia no tiene pantalla. Un item de
 * menu que lleva a un 404 le enseña al usuario a desconfiar del menu entero.
 */
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { seccionesVisibles } from '@/lib/secciones';

function esActual(pathname: string, href: string): boolean {
  // `/` solo coincide exacto: si no, seria "actual" en todas las rutas.
  return href === '/' ? pathname === '/' : pathname.startsWith(href);
}

export function NavegacionPrincipal() {
  const pathname = usePathname();

  return (
    <header className="border-b border-neutro-borde">
      <nav aria-label="Principal" className="mx-auto flex max-w-4xl items-center gap-6 p-4">
        <span className="font-semibold tracking-tight">deRuedas</span>

        <ul className="flex gap-4 text-sm">
          {seccionesVisibles().map((seccion) => {
            const actual = esActual(pathname, seccion.href);
            return (
              <li key={seccion.href}>
                <Link
                  href={seccion.href}
                  // `aria-current` y no solo un color: quien navega con lector
                  // de pantalla no ve el subrayado.
                  aria-current={actual ? 'page' : undefined}
                  className={
                    actual
                      ? 'font-medium text-neutro-enfasis underline underline-offset-4'
                      : 'text-neutro-texto hover:text-neutro-enfasis'
                  }
                >
                  {seccion.etiqueta}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
