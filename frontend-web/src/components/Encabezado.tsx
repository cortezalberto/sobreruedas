/**
 * Encabezado del shell — C-07, `T-038`.
 *
 * Server component a proposito: no tiene estado ni escucha eventos. Lo unico
 * interactivo del shell es la barra lateral, que necesita `usePathname` para
 * marcar donde estas. Separarlos es lo que evita arrastrar todo el encabezado
 * al cliente por una sola linea de interactividad.
 *
 * EL HUECO DE LA DERECHA ESTA VACIO Y NO ES UN OLVIDO
 * ────────────────────────────────────────────────────
 * Ahi van el usuario y la agencia activa, y las dos cosas salen de la identidad
 * —C-08 en el frontend, que espera a C-05 en el backend, que espera a `E-001`—.
 * Poner un avatar de mentira o un "Mi cuenta" que no lleva a ningun lado seria
 * el mismo error que el proyecto ya se marco dos veces: prometer en la interfaz
 * algo que el sistema no puede cumplir.
 *
 * El slot existe para que cuando la identidad llegue no haya que rearmar el
 * layout: se llena, no se reacomoda.
 */
import Link from 'next/link';
import type { ReactNode } from 'react';

/**
 * El encabezado NO importa el stack de autenticacion, y eso es deliberado.
 *
 * `identidad` es un slot que llena el layout. Importar `@/auth` aca arrastraria
 * NextAuth —y con el `next/server`— dentro de un componente de presentacion, y
 * el test del shell dejaria de poder montarlo en jsdom. Paso: el commit que
 * cablea la sesion rompio `shell.test.tsx` sin tocarlo.
 *
 * Ademas de testeable, es correcto: un encabezado no deberia saber COMO se
 * resuelve la identidad, solo donde va.
 */
export function Encabezado({ identidad }: { identidad?: ReactNode }) {
  return (
    <header className="border-b border-neutro-borde">
      <div className="flex h-14 items-center justify-between px-4">
        {/* El nombre lleva al inicio. Es la convencion que nadie tiene que
            aprender, y es lo que hace que el logo no sea decorativo. */}
        <Link href="/" className="font-semibold tracking-tight text-neutro-enfasis">
          deRuedas
        </Link>

        {/* Slot de identidad — lo llena el layout. Ver el encabezado. */}
        {identidad ?? <div />}
      </div>
    </header>
  );
}
