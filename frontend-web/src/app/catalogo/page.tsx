/**
 * Catalogo de marcas — C-13.
 *
 * Segundo recorrido completo del sistema, con las 40 marcas que sembro la
 * migracion `009`. Mismo patron que `/planes`: Server Component, `force-dynamic`
 * para que el build no dependa del backend, y los boundaries de carga y error
 * en archivos hermanos.
 *
 * NO es el selector en cascada de C-13. Ese necesita el design system (C-07),
 * que todavia no existe — riesgo `R-4`. Esto es navegacion en dos pasos: se
 * elige marca y se ven sus modelos.
 */
import Link from 'next/link';

import { obtenerMarcas } from '@/lib/api';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Catalogo — deRuedas Gestion',
};

export default async function CatalogoPage() {
  const marcas = await obtenerMarcas();

  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-3xl font-semibold tracking-tight">Catalogo</h1>
      <p className="mt-2 text-neutro-texto">
        {marcas.length} marcas del mercado argentino. Catalogo compartido: lo lee cualquier agencia
        y no lo escribe ninguna.
      </p>

      <ul className="mt-8 grid gap-2 sm:grid-cols-3">
        {marcas.map((marca) => (
          <li key={marca.id}>
            <Link
              href={`/catalogo/${marca.slug}`}
              className="block rounded-lg border border-neutro-borde p-3 hover:border-marca"
            >
              <span className="font-medium">{marca.name}</span>
              {marca.origin_country && (
                <span className="block text-xs text-neutro-suave">{marca.origin_country}</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}
