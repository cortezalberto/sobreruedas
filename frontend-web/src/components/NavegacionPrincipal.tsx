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
 * ⚠️ Provisorio en lo visual, no en la estructura. El design system es C-07
 * (riesgo `R-4`: la especificacion todavia no existe), asi que los colores y
 * espaciados de aca son de andamio y se reemplazan. Lo que no cambia es que la
 * navegacion viva en un solo lugar.
 */
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface Seccion {
  href: string;
  etiqueta: string;
}

const SECCIONES: readonly Seccion[] = [
  { href: '/', etiqueta: 'Inicio' },
  { href: '/planes', etiqueta: 'Planes' },
  { href: '/catalogo', etiqueta: 'Catalogo' },
];

function esActual(pathname: string, href: string): boolean {
  // `/` solo coincide exacto: si no, seria "actual" en todas las rutas.
  return href === '/' ? pathname === '/' : pathname.startsWith(href);
}

export function NavegacionPrincipal() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-200">
      <nav aria-label="Principal" className="mx-auto flex max-w-4xl items-center gap-6 p-4">
        <span className="font-semibold tracking-tight">deRuedas</span>

        <ul className="flex gap-4 text-sm">
          {SECCIONES.map((seccion) => {
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
                      ? 'font-medium text-slate-900 underline underline-offset-4'
                      : 'text-slate-600 hover:text-slate-900'
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
