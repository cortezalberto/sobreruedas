/**
 * Quién está en sesión, y el botón para entrar o salir.
 *
 * Es un Server Component: `auth()` lee la cookie de sesión en el servidor, así
 * que el token no hace falta acá y no viaja al cliente por este camino.
 *
 * El `signIn`/`signOut` van en Server Actions y no en handlers de cliente, por
 * lo mismo: el redirect a Keycloak lo arma el servidor.
 */

import { auth, signIn, signOut } from '@/auth';

// Desde `lib/tokens` y NO desde `components/ui`: ese modulo es `'use client'`,
// y una constante exportada desde ahi le llega rota a un Server Component
// —pasa el build, pasan los tests, y la pagina queda en blanco (commit cf0f311)—.
import { SUPERFICIE_DE_TARJETA } from '@/lib/tokens';

function Boton({ children }: { children: React.ReactNode }) {
  return (
    <button
      type="submit"
      className="rounded-md border border-[var(--borde)] px-3 py-1.5 text-sm font-medium hover:bg-[var(--superficie-2)]"
    >
      {children}
    </button>
  );
}

export async function Sesion() {
  const sesion = await auth();

  if (!sesion?.user) {
    return (
      <form
        action={async () => {
          'use server';
          await signIn('keycloak');
        }}
      >
        <Boton>Iniciar sesión</Boton>
      </form>
    );
  }

  return (
    <div className={`flex items-center gap-3 ${SUPERFICIE_DE_TARJETA} px-3 py-1.5`}>
      <span className="text-sm">
        {/* `name` sale del token de Keycloak; el nombre "de negocio" lo tiene
            `GET /auth/me`, que es el espejo local. Acá alcanza con el del token
            para no pegarle al backend en cada render del encabezado. */}
        {sesion.user.name ?? sesion.user.email}
      </span>
      <form
        action={async () => {
          'use server';
          // Cierra NUESTRA sesión. La de Keycloak sigue viva hasta que venza o
          // hasta que se haga un `end-session` — es la consecuencia asumida que
          // `design.md` D-4 documenta para `POST /auth/logout`.
          await signOut({ redirectTo: '/' });
        }}
      >
        <Boton>Salir</Boton>
      </form>
    </div>
  );
}
