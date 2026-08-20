'use client';

/**
 * Los botones de cambio de estado de una fila del stock.
 *
 * OFRECE LO QUE LA MAQUINA DE ESTADOS ADMITE, NO LO QUE EL ROL PUEDE. Esa
 * división la fija `ADR-034`: `RN-ST-05` dice qué transiciones existen —dominio,
 * igual para todos— y la matriz dice quién hace cada una. Si el rol no
 * corresponde, el backend responde 403 y el mensaje aparece acá.
 *
 * Es deliberado ofrecer un botón que puede fallar. La alternativa —copiar la
 * matriz al cliente para esconderlo— daría una segunda fuente de verdad sobre
 * permisos, editable con las herramientas del navegador, y que se desincroniza
 * en silencio. Un rechazo explicado es mejor que un permiso adivinado.
 */

import { useState, useTransition } from 'react';

import { cambiarEstado } from '@/app/stock/acciones';
import { nombreDeEstado, transicionesDesde } from '@/lib/stock';

export function CambiarEstado({ vehiculoId, estado }: { vehiculoId: string; estado: string }) {
  const [mensaje, setMensaje] = useState<{ ok: boolean; texto: string } | null>(null);
  const [enCurso, empezar] = useTransition();

  const destinos = transicionesDesde(estado);

  if (destinos.length === 0) {
    return <span className="text-xs text-neutro-texto">—</span>;
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {destinos.map((destino) => (
        <button
          key={destino}
          type="button"
          disabled={enCurso}
          onClick={() => {
            setMensaje(null);
            empezar(async () => {
              const r = await cambiarEstado(vehiculoId, destino);
              setMensaje({ ok: r.ok, texto: r.mensaje });
            });
          }}
          className="hover:bg-neutro-superficie rounded border border-neutro-borde px-2 py-0.5 text-xs disabled:opacity-50"
        >
          {nombreDeEstado(destino)}
        </button>
      ))}

      {mensaje && (
        // `role="status"` y no un `<p>` suelto: un lector de pantalla tiene que
        // anunciar el resultado, que es la única señal de que el botón hizo algo.
        <span
          role="status"
          className={`text-xs ${mensaje.ok ? 'text-estado-exito' : 'text-estado-error'}`}
        >
          {mensaje.texto}
        </span>
      )}
    </div>
  );
}
