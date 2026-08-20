/**
 * El stock de la agencia — la pantalla que reemplaza a la planilla.
 *
 * Es el primer recorrido COMPLETO del sistema con identidad: navegador →
 * Keycloak → sesión → Next → FastAPI → RBAC → RLS → PostgreSQL. Todo lo
 * anterior era catálogo público.
 *
 * LO QUE SE VE DEPENDE DE QUIÉN MIRA, y no por una condición de esta página.
 * La columna de costo aparece o no según lo que **el backend devuelva**:
 * `RN-ST-12` hace que la clave `acquisition_cost_ars` ni siquiera viaje para un
 * `salesperson`. Acá no hay ningún `if (rol === ...)` — si lo hubiera, sería una
 * segunda copia de la matriz de permisos, y la copia del cliente es la que se
 * puede editar con las herramientas del navegador.
 *
 * SERVER COMPONENT. El token sale de la sesión en el servidor y el fetch corre
 * en el proceso de Next, así que el token no viaja al navegador por este camino
 * y CORS no interviene.
 */
import { auth } from '@/auth';
import { CambiarEstado } from '@/components/CambiarEstado';
import { Alerta, Etiqueta, EstadoVacio, Tabla } from '@/components/ui';
import { obtenerMarcasPorId, obtenerVehiculos, type Vehiculo } from '@/lib/api';
import { columnasPara, elBackendMandaElCosto, nombreDeEstado } from '@/lib/stock';

/** Los tonos que `Etiqueta` admite. Se declara acá para que agregar un estado
 *  con un tono inexistente lo marque `tsc` y no el navegador. */
type TonoDeEstado = 'neutro' | 'exito' | 'advertencia' | 'meta';

/** Ver el comentario de `/planes`: el build no puede depender de la API. */
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Stock',
};

const PESOS = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
});

const KILOMETROS = new Intl.NumberFormat('es-AR');

/**
 * El tono de cada estado. El NOMBRE sale de `lib/stock.ts`, que es la fuente
 * unica — acá solo vive el color, que es decisión de esta pantalla.
 */
const TONO_DE_ESTADO: ReadonlyMap<string, TonoDeEstado> = new Map([
  ['in_preparation', 'neutro'],
  ['available', 'exito'],
  ['reserved', 'advertencia'],
  ['sold', 'meta'],
  ['in_workshop', 'advertencia'],
  ['archived', 'neutro'],
]);

function Fila({
  vehiculo,
  marca,
  muestraElCosto,
}: {
  vehiculo: Vehiculo;
  marca: string;
  muestraElCosto: boolean;
}) {
  const tono = TONO_DE_ESTADO.get(vehiculo.status) ?? 'neutro';

  return (
    <tr className="border-b border-neutro-borde">
      <td className="py-2 pr-4 font-mono">
        {/* `ADR-031`: el dominio es opcional — un 0 km sin patentar no tiene.
            Se cae al chasis antes de mostrar un guión. */}
        {vehiculo.domain_plate ?? vehiculo.chassis_number ?? '—'}
      </td>
      <td className="py-2 pr-4">{marca}</td>
      <td className="py-2 pr-4">{vehiculo.year}</td>
      <td className="py-2 pr-4">{vehiculo.color}</td>
      <td className="py-2 pr-4 text-right tabular-nums">
        {KILOMETROS.format(vehiculo.mileage_km)} km
      </td>
      <td className="py-2 pr-4 text-right tabular-nums">
        {PESOS.format(Number(vehiculo.price_ars))}
      </td>
      {muestraElCosto && (
        <td className="py-2 pr-4 text-right tabular-nums">
          {vehiculo.acquisition_cost_ars
            ? PESOS.format(Number(vehiculo.acquisition_cost_ars))
            : '—'}
        </td>
      )}
      <td className="py-2 pr-4">
        <Etiqueta tono={tono}>{nombreDeEstado(vehiculo.status)}</Etiqueta>
      </td>
      <td className="py-2">
        <CambiarEstado vehiculoId={vehiculo.id} estado={vehiculo.status} />
      </td>
    </tr>
  );
}

export default async function StockPage() {
  const sesion = await auth();

  if (!sesion?.accessToken) {
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Stock</h1>
        <EstadoVacio
          titulo="Hace falta iniciar sesión"
          descripcion="El stock es de una agencia, así que no se puede mostrar sin saber de cuál."
        />
      </div>
    );
  }

  let vehiculos: Vehiculo[];
  let marcas: ReadonlyMap<string, string>;
  try {
    [vehiculos, marcas] = await Promise.all([
      obtenerVehiculos(sesion.accessToken),
      obtenerMarcasPorId(),
    ]);
  } catch (error) {
    // Se registra del lado del SERVIDOR antes de mostrar el cartel. Un `catch`
    // mudo convierte cualquier causa —token vencido, backend caido, contrato
    // cambiado— en el mismo mensaje inutil, y despues hay que reproducirlo a
    // mano para saber que paso. El usuario ve el cartel; el log ve el motivo.
    console.error('[stock] no se pudo cargar el stock:', error);
    return (
      <div className="mx-auto max-w-5xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Stock</h1>
        <Alerta tono="error" titulo="No se pudo cargar el stock">
          El servicio no respondió. Si estás en desarrollo, revisá que el backend esté levantado.
        </Alerta>
      </div>
    );
  }

  const muestraElCosto = elBackendMandaElCosto(vehiculos);
  const columnas = columnasPara(vehiculos);

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Stock</h1>
      <p className="mb-6 text-sm text-neutro-texto">
        {vehiculos.length === 1 ? '1 vehículo' : `${vehiculos.length} vehículos`} de tu agencia.
        {!muestraElCosto && ' El precio de costo no está disponible para tu rol.'}
      </p>

      {vehiculos.length === 0 ? (
        <EstadoVacio
          titulo="Todavía no hay vehículos"
          descripcion="Cuando cargues el primero, o importes una planilla, aparecen acá."
        />
      ) : (
        <Tabla descripcion="Vehículos de la agencia" columnas={columnas}>
          {vehiculos.map((vehiculo) => (
            <Fila
              key={vehiculo.id}
              vehiculo={vehiculo}
              marca={marcas.get(vehiculo.brand_id) ?? '—'}
              muestraElCosto={muestraElCosto}
            />
          ))}
        </Tabla>
      )}
    </div>
  );
}
