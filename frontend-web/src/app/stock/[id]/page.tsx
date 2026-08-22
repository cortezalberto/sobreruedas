/**
 * La ficha de un vehículo — el último pendiente del día 3 de `ESC-003`.
 *
 * EL ENDPOINT YA ESTABA Y NADIE LO CONSUMÍA. `GET /api/v1/vehicles/{id}` existe
 * desde C-15 con su `require_permission("vehicles:read")` puesto; lo que faltaba
 * era la pantalla. Por eso este archivo no agrega ni un contrato nuevo: usa el
 * que ya estaba escrito y probado del otro lado.
 *
 * LA MISMA DIVISIÓN DE SIEMPRE (`ADR-034`): acá no hay ningún `if (rol === ...)`.
 * El costo de adquisición aparece porque **el backend lo mandó** —`RN-ST-12` hace
 * que la clave ni siquiera viaje para un `salesperson`—, no porque esta página
 * pregunte quién mira. Y los botones de cambio de estado ofrecen lo que la
 * máquina de estados admite; si el rol no corresponde, el backend responde 403 y
 * el mensaje aparece al lado del botón.
 *
 * SERVER COMPONENT, igual que el listado: el token sale de la sesión en el
 * servidor y el fetch corre en el proceso de Next, así que no viaja al navegador
 * por este camino y CORS no interviene.
 */
import Link from 'next/link';
import { notFound } from 'next/navigation';
import type { ReactNode } from 'react';

import { auth } from '@/auth';
import { CambiarEstado } from '@/components/CambiarEstado';
import { Alerta, Etiqueta, EstadoVacio, Migas, Tarjeta } from '@/components/ui';
import {
  obtenerMarcasPorId,
  obtenerModelos,
  obtenerTodasLasSucursales,
  obtenerVehiculo,
  type Sucursal,
  type Vehiculo,
} from '@/lib/api';
import { formatearFecha, nombreDeEstado, noHayTalVehiculo, textoDeCatalogo } from '@/lib/stock';
import { CARROCERIAS, COMBUSTIBLES, TRANSMISIONES } from '@/lib/vehiculo-nuevo';

/** Los tonos que `Etiqueta` admite, igual que en el listado. */
type TonoDeEstado = 'neutro' | 'exito' | 'advertencia' | 'meta';

/** Ver el comentario de `/planes`: el build no puede depender de la API. */
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Ficha del vehículo',
};

const PESOS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
});

const DOLARES = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});

const KILOMETROS = new Intl.NumberFormat('es-AR');

const TONO_DE_ESTADO: ReadonlyMap<string, TonoDeEstado> = new Map([
  ['in_preparation', 'neutro'],
  ['available', 'exito'],
  ['reserved', 'advertencia'],
  ['sold', 'meta'],
  ['in_workshop', 'advertencia'],
  ['archived', 'neutro'],
]);

/**
 * Un par etiqueta/valor.
 *
 * `<dl>`/`<dt>`/`<dd>` y no `<div>`s: un lector de pantalla anuncia "Combustible,
 * Nafta" como una unidad, y con `div`s leería dos textos sueltos sin relación.
 *
 * Vive acá y no en `components/ui` a propósito: hoy tiene un solo consumidor.
 * Subirlo al conjunto de primitivos lo obligaría a la auditoría de contraste y
 * al snapshot de `T-038` sin que nadie más lo use — cuando aparezca el segundo
 * consumidor, ahí sí.
 */
function Dato({ etiqueta, children }: { etiqueta: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-neutro-texto">{etiqueta}</dt>
      <dd className="mt-0.5 text-sm text-neutro-enfasis">{children}</dd>
    </div>
  );
}

function Bloque({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <Tarjeta>
      <h2 className="mb-3 text-sm font-semibold tracking-tight text-neutro-enfasis">{titulo}</h2>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">{children}</dl>
    </Tarjeta>
  );
}

export default async function FichaDeVehiculoPage({ params }: { params: Promise<{ id: string }> }) {
  // En Next 16 `params` es una promesa. Ver el comentario de `/catalogo/[marca]`.
  const { id } = await params;

  const sesion = await auth();

  if (!sesion?.accessToken) {
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Vehículo</h1>
        <EstadoVacio
          titulo="Hace falta iniciar sesión"
          descripcion="La ficha es de un vehículo de una agencia, así que no se puede mostrar sin saber de cuál."
        />
      </div>
    );
  }

  let vehiculo: Vehiculo;
  try {
    vehiculo = await obtenerVehiculo(id, sesion.accessToken);
  } catch (error) {
    // "ACA NO HAY NADA" NO ES UNA FALLA, y son dos estados HTTP: el 404 del id
    // que no tiene fila y el 422 del id que ni siquiera es un UUID. Los dos van a
    // `notFound()`. El detalle está en `noHayTalVehiculo`, que vive en `lib/`
    // para poder probarse sin montar NextAuth.
    if (noHayTalVehiculo(error)) notFound();

    // Ver el comentario del `catch` del listado: el usuario ve el cartel, el log
    // ve la causa.
    console.error('[stock] no se pudo cargar la ficha:', error);
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Vehículo</h1>
        <Alerta tono="error" titulo="No se pudo cargar la ficha">
          El servicio no respondió. Si estás en desarrollo, revisá que el backend esté levantado.
        </Alerta>
      </div>
    );
  }

  // Los tres nombres que el vehículo trae como id. Van DESPUÉS del vehículo y no
  // junto a él: sin `brand_id` no se sabe a qué marca pedirle los modelos, y
  // traer los de las cuarenta marcas para resolver uno sería absurdo.
  //
  // Ninguno es esencial para la ficha, así que un fallo acá no puede tumbar la
  // página: se resuelven con `catch` a vacío y el campo cae al guión. El dato del
  // vehículo ya está, y es lo que esta pantalla vino a mostrar.
  const [marcas, modelos, sucursales] = await Promise.all([
    obtenerMarcasPorId().catch((): ReadonlyMap<string, string> => new Map()),
    obtenerModelos(vehiculo.brand_id).catch(() => []),
    obtenerTodasLasSucursales(sesion.accessToken).catch((): Sucursal[] => []),
  ]);

  const marca = marcas.get(vehiculo.brand_id) ?? '—';
  const modelo = modelos.find((m) => m.id === vehiculo.model_id)?.name ?? '—';
  const sucursal = sucursales.find((s) => s.id === vehiculo.branch_id);
  const tono = TONO_DE_ESTADO.get(vehiculo.status) ?? 'neutro';

  // `in` y no `!= null`: la clave AUSENTE significa "tu rol no lo ve" y la clave
  // en `null` significa "lo ves, y este vehículo no lo tiene cargado". Es la
  // misma pregunta que hace `elBackendMandaElCosto` para decidir la columna del
  // listado, sobre un vehículo en vez de sobre la lista.
  const muestraElCosto = 'acquisition_cost_ars' in vehiculo;

  // `ADR-031`: el dominio es opcional —un 0 km sin patentar no tiene— y se cae al
  // chasis antes de mostrar un guión. Mismo criterio que la primera columna del
  // listado, para que la fila y el título de su ficha digan lo mismo.
  const identificador = vehiculo.domain_plate ?? vehiculo.chassis_number ?? 'Sin identificar';

  return (
    <div className="mx-auto max-w-5xl">
      <div className="mb-4">
        <Migas tramos={[{ texto: 'Stock', href: '/stock' }, { texto: identificador }]} />
      </div>

      <div className="mb-6 flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {marca} {modelo}
          </h1>
          <p className="mt-1 text-sm text-neutro-texto">
            {vehiculo.year} · {vehiculo.color} · {KILOMETROS.format(vehiculo.mileage_km)} km
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Etiqueta tono={tono}>{nombreDeEstado(vehiculo.status)}</Etiqueta>
          <CambiarEstado vehiculoId={vehiculo.id} estado={vehiculo.status} />
        </div>
      </div>

      <div className="grid gap-4">
        <Bloque titulo="Identificación">
          {/* Los dos se muestran aunque uno esté vacío: `ADR-031` admite que falte
              cualquiera de los dos, y esconder el vacío dejaría al usuario sin
              saber si el dato no está o si la ficha no lo muestra. */}
          <Dato etiqueta="Dominio">
            <span className="font-mono">{vehiculo.domain_plate ?? '—'}</span>
          </Dato>
          <Dato etiqueta="Chasis">
            <span className="font-mono">{vehiculo.chassis_number ?? '—'}</span>
          </Dato>
          <Dato etiqueta="Marca">{marca}</Dato>
          <Dato etiqueta="Modelo">{modelo}</Dato>
          <Dato etiqueta="Año">{vehiculo.year}</Dato>
          <Dato etiqueta="Color">{vehiculo.color}</Dato>
        </Bloque>

        <Bloque titulo="Ficha técnica">
          <Dato etiqueta="Combustible">{textoDeCatalogo(COMBUSTIBLES, vehiculo.fuel_type)}</Dato>
          <Dato etiqueta="Transmisión">
            {textoDeCatalogo(TRANSMISIONES, vehiculo.transmission)}
          </Dato>
          <Dato etiqueta="Carrocería">{textoDeCatalogo(CARROCERIAS, vehiculo.body_type)}</Dato>
          <Dato etiqueta="Kilómetros">
            <span className="tabular-nums">{KILOMETROS.format(vehiculo.mileage_km)} km</span>
          </Dato>
        </Bloque>

        <Bloque titulo="Precio">
          <Dato etiqueta="Precio de venta">
            <span className="tabular-nums">{PESOS.format(Number(vehiculo.price_ars))}</span>
          </Dato>
          <Dato etiqueta="Precio en dólares">
            <span className="tabular-nums">
              {vehiculo.price_usd === null ? '—' : DOLARES.format(Number(vehiculo.price_usd))}
            </span>
          </Dato>
          {muestraElCosto && (
            <Dato etiqueta="Costo de adquisición">
              <span className="tabular-nums">
                {vehiculo.acquisition_cost_ars
                  ? PESOS.format(Number(vehiculo.acquisition_cost_ars))
                  : '—'}
              </span>
            </Dato>
          )}
        </Bloque>

        <Bloque titulo="Ubicación y fechas">
          {/* La sucursal puede estar dada de baja y su nombre igual se muestra: el
              vehículo está ahí, y el soft delete la conserva justamente para que
              la ficha pueda nombrarla. Por eso se piden TODAS. */}
          <Dato etiqueta="Sucursal">
            {sucursal === undefined ? (
              '—'
            ) : (
              <>
                {sucursal.name}
                {!sucursal.is_active && (
                  <span className="ml-2 text-xs text-neutro-texto">(dada de baja)</span>
                )}
              </>
            )}
          </Dato>
          <Dato etiqueta="Adquirido">{formatearFecha(vehiculo.acquired_at)}</Dato>
          <Dato etiqueta="Vendido">{formatearFecha(vehiculo.sold_at)}</Dato>
          <Dato etiqueta="Cargado">{formatearFecha(vehiculo.created_at)}</Dato>
        </Bloque>

        <Tarjeta>
          <h2 className="mb-3 text-sm font-semibold tracking-tight text-neutro-enfasis">
            Descripción y equipamiento
          </h2>
          <p className="text-sm text-neutro-enfasis">
            {vehiculo.description ?? 'Sin descripción cargada.'}
          </p>
          {vehiculo.features.length > 0 && (
            <ul className="mt-3 flex flex-wrap gap-2">
              {vehiculo.features.map((caracteristica) => (
                <li key={caracteristica}>
                  <Etiqueta>{caracteristica}</Etiqueta>
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      </div>

      <p className="mt-6 text-sm">
        <Link href="/stock" className="underline underline-offset-4 hover:text-marca">
          Volver al stock
        </Link>
      </p>
    </div>
  );
}
