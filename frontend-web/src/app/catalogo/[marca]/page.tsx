/**
 * Modelos de una marca — C-13.
 *
 * El 404 del backend NO se traduce a lista vacia. Si la marca no existe, el
 * cliente levanta `ErrorDeApi` y el boundary de error lo muestra: "no hay
 * modelos cargados" y "esa marca no existe" son cosas distintas, y el backend
 * se tomo el trabajo de distinguirlas.
 */
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { EstadoVacio } from '@/components/ui';
import { ErrorDeApi, obtenerModelos, type Modelo } from '@/lib/api';

export const dynamic = 'force-dynamic';

/** `null` = se sigue vendiendo. Ver el contrato en `lib/api.ts`. */
function vigencia(modelo: Modelo): string {
  return modelo.year_to === null
    ? `${modelo.year_from} — actual`
    : `${modelo.year_from}–${modelo.year_to}`;
}

export default async function ModelosDeMarcaPage({
  params,
}: {
  params: Promise<{ marca: string }>;
}) {
  // En Next 16 `params` es una promesa: la ruta puede resolverse despues de
  // empezar a renderizar.
  const { marca } = await params;

  // Un 404 del backend NO es un error de la aplicacion: es una marca que no
  // existe. `notFound()` renderiza la pagina de no encontrado, y el boundary de
  // error queda para lo que si es una falla —el backend caido, una respuesta
  // con forma inesperada—.
  //
  // Sin esto, pedir /catalogo/ferrari mostraba "el servicio no respondio", y el
  // servicio habia respondido perfectamente: con un 404. Es la misma distincion
  // que el endpoint se tomo el trabajo de hacer, perdida en la pantalla.
  let modelos: Modelo[];
  try {
    modelos = await obtenerModelos(marca);
  } catch (error) {
    if (error instanceof ErrorDeApi && error.estado === 404) notFound();
    throw error;
  }

  return (
    <main className="mx-auto max-w-4xl p-8">
      <Link href="/catalogo" className="text-sm text-neutro-texto underline underline-offset-4">
        ← Catalogo
      </Link>

      <h1 className="mt-4 text-3xl font-semibold capitalize tracking-tight">
        {marca.replace(/-/g, ' ')}
      </h1>

      {modelos.length === 0 ? (
        <EstadoVacio
          titulo="Esta marca todavia no tiene modelos cargados"
          descripcion="El catalogo se completa con datos de mercado."
        />
      ) : (
        <ul className="mt-8 divide-y divide-neutro-borde border-y border-neutro-borde">
          {modelos.map((modelo) => (
            <li key={modelo.id} className="flex items-baseline justify-between gap-4 py-3">
              <span className="font-medium">{modelo.name}</span>
              <span className="text-sm text-neutro-suave">
                {modelo.body_type} · {vigencia(modelo)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
