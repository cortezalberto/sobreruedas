/**
 * Grilla de planes — el primer recorrido completo del sistema.
 *
 * Next.js -> HTTP -> FastAPI -> SQLAlchemy -> PostgreSQL, con los datos que
 * sembro la migracion `005_planes`. Nada mockeado.
 *
 * ES UN SERVER COMPONENT, Y NO POR MODA. El fetch corre en el proceso de Next,
 * no en el navegador, asi que:
 *
 *   - no interviene CORS — el backend solo permite `localhost:3000` por
 *     default, y esta maquina sirve el front en 3010;
 *   - la URL del backend no viaja al cliente;
 *   - no hace falta estado de carga: la pagina llega armada.
 *
 * El dia que haya una vista interactiva —filtros, paginado— ahi entra TanStack
 * Query del lado del cliente. Para una grilla que se lee y no se toca, seria
 * maquinaria sin trabajo que hacer.
 */
import { obtenerPlanes, SIN_TECHO, type Plan } from '@/lib/api';

/**
 * SE RENDERIZA POR PEDIDO, NO EN EL BUILD. No es una preferencia: el build no
 * puede depender de que el backend este vivo.
 *
 * Sin esto Next prerenderiza `/planes` al compilar, sale a buscar los planes en
 * ese momento y el build falla con ECONNREFUSED donde no haya API escuchando.
 * Paso exactamente eso en CI, y en local no se vio porque el backend estaba
 * corriendo.
 *
 * Y no es un problema solo de CI: por `ADR-023` la imagen se construye en el
 * runner y el VPS la baja despues. En el runner no hay —ni debe haber— acceso a
 * la base de produccion, asi que una pagina que necesita la API para compilar
 * no se puede empaquetar.
 *
 * El cacheo no se pierde: vive en el `revalidate` del fetch (`lib/api.ts`), que
 * es cache de datos y no de build.
 */
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Planes — deRuedas Gestion',
};

const PESOS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
});

/**
 * `1 sucursales` no lo escribe nadie, y era lo que mostraba Starter.
 *
 * El singular se pide explicito en vez de sacarle la `s` al plural: en
 * castellano no siempre alcanza —`sucursales` pierde `es`, no `s`— y una regla
 * que acierta en tres casos de cuatro es peor que no tener regla.
 */
function limite(valor: number, singular: string, plural: string): string {
  if (valor === SIN_TECHO) return `${plural} ilimitados`;
  return valor === 1 ? `1 ${singular}` : `${valor} ${plural}`;
}

function TarjetaDePlan({ plan }: { plan: Plan }) {
  return (
    <article className="rounded-lg border border-slate-200 p-5">
      <h2 className="text-lg font-semibold capitalize tracking-tight">{plan.name}</h2>

      <p className="mt-1 text-2xl font-semibold">
        {PESOS.format(Number(plan.price_ars))}
        <span className="text-sm font-normal text-slate-500"> /mes</span>
      </p>

      <ul className="mt-4 space-y-1 text-sm text-slate-700">
        <li>{limite(plan.max_users, 'usuario', 'usuarios')}</li>
        <li>{limite(plan.max_vehicles, 'vehiculo', 'vehiculos')}</li>
        <li>{limite(plan.max_branches, 'sucursal', 'sucursales')}</li>
        <li>
          {limite(
            plan.max_whatsapp_messages_month,
            'mensaje de WhatsApp por mes',
            'mensajes de WhatsApp por mes',
          )}
        </li>
      </ul>

      <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">
        {plan.modules.length} modulos
      </p>
    </article>
  );
}

export default async function PlanesPage() {
  const planes = await obtenerPlanes();

  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Planes</h1>
      <p className="mt-2 text-slate-600">
        Datos servidos por el backend desde PostgreSQL. Sin mocks.
      </p>

      <div className="mt-8 grid gap-4 sm:grid-cols-3">
        {planes.map((plan) => (
          <TarjetaDePlan key={plan.id} plan={plan} />
        ))}
      </div>
    </main>
  );
}
