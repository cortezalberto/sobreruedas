import Link from 'next/link';

/**
 * Home — T-006.
 *
 * ⚠️ T-006 pide ademas que esta pagina "redirija a /login si no hay sesion".
 * NO SE IMPLEMENTA ACA, y no es un olvido: no existe ni el mecanismo de sesion
 * ni la ruta /login. La autenticacion se delega enteramente a Keycloak
 * (ADR-007) y su integracion con NextAuth es C-05.
 *
 * La tarea 7.6 de este change ya dejo el redirect fuera de alcance. Un
 * redirect a una ruta que no existe seria un 404 disfrazado de feature.
 *
 * El texto decia "todavia no hay funcionalidad de negocio", y desde que existe
 * `/planes` eso dejo de ser cierto. Se corrige acordando con lo que hay: es el
 * mismo defecto que este proyecto viene encontrando en sus documentos, y una
 * pantalla que describe mal el sistema no es distinta de un ADR que lo hace.
 */
export default function HomePage() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-3xl font-semibold tracking-tight">deRuedas Gestion</h1>
      <p className="mt-2 text-neutro-texto">Sistema de gestion para agencias de vehiculos.</p>

      <div className="mt-8 rounded-lg border border-neutro-borde p-4">
        <h2 className="font-medium">
          <Link href="/planes" className="underline underline-offset-4 hover:text-neutro-texto">
            Planes
          </Link>
        </h2>
        <p className="mt-1 text-sm text-neutro-texto">
          El catalogo comercial, servido por el backend desde PostgreSQL.
        </p>
      </div>

      <div className="mt-4 rounded-lg border border-neutro-borde bg-neutro-fondo p-4 text-sm text-neutro-texto">
        <p className="font-medium">Ola 0 — fundacion</p>
        <p className="mt-1">
          Lo que se ve es catalogo publico. Todo lo que dependa de una agencia necesita identidad, y
          el inicio de sesion contra Keycloak entra con C-05. El design system, con C-07.
        </p>
      </div>
    </div>
  );
}
