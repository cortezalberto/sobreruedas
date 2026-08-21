/**
 * Cargar un vehículo — el último tramo de la rebanada vertical de `ESC-003`.
 *
 * SERVER COMPONENT que solo junta los datos que el formulario necesita para
 * existir: las sucursales de la agencia y las marcas del catálogo. Lo que tiene
 * estado —el borrador, la cascada marca → modelo— es el client component que
 * monta abajo.
 *
 * RUTA PROPIA Y NO UN MODAL. Son catorce campos: en el modal de 32 rem quedan
 * apretados y con scroll interno, y encima `Modal` trae su propio botón de
 * cerrar al pie, que al lado de "Cargar vehículo" se lee como el par
 * Aceptar/Cancelar sin serlo. Con ruta propia, además, el alta se puede
 * enlazar, recargar y volver atrás con el botón del navegador.
 *
 * EL ORDEN DE LOS PEDIDOS NO ES CASUAL: si las sucursales fallan no hay
 * formulario posible —`branch_id` es obligatorio— y por eso corta acá. Si
 * fallara el catálogo pasa lo mismo con la marca, así que van juntos.
 */
import Link from 'next/link';

import { auth } from '@/auth';
import { FormularioDeVehiculo } from '@/components/FormularioDeVehiculo';
import { Alerta, EstadoVacio, Migas } from '@/components/ui';
import { obtenerMarcas, obtenerSucursales, type Marca, type Sucursal } from '@/lib/api';

/** Ver el comentario de `/planes`: el build no puede depender de la API. */
export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Cargar vehículo',
};

export default async function NuevoVehiculoPage() {
  const sesion = await auth();

  if (!sesion?.accessToken) {
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Cargar vehículo</h1>
        <EstadoVacio
          titulo="Hace falta iniciar sesión"
          descripcion="Un vehículo se carga en una agencia, así que no se puede sin saber en cuál."
        />
      </div>
    );
  }

  let sucursales: Sucursal[];
  let marcas: Marca[];
  try {
    [sucursales, marcas] = await Promise.all([
      obtenerSucursales(sesion.accessToken),
      obtenerMarcas(),
    ]);
  } catch (error) {
    // El motivo va al log del servidor y el cartel al usuario — mismo criterio
    // que la tabla de stock. Un `catch` mudo convierte token vencido, backend
    // caído y contrato cambiado en el mismo mensaje inútil.
    console.error('[stock] no se pudo preparar el alta:', error);
    return (
      <div className="mx-auto max-w-3xl">
        <h1 className="mb-6 text-2xl font-semibold tracking-tight">Cargar vehículo</h1>
        <Alerta tono="error" titulo="No se pudo abrir el alta">
          No se pudieron cargar las sucursales o el catálogo. Si estás en desarrollo, revisá que el
          backend esté levantado.
        </Alerta>
      </div>
    );
  }

  // Sin una sola sucursal activa el formulario no se puede completar: `branch_id`
  // es obligatorio. Mostrar el formulario con el desplegable vacío dejaría al
  // usuario buscando qué hizo mal ante un campo que nunca va a tener opciones.
  if (sucursales.length === 0) {
    return (
      <div className="mx-auto max-w-3xl">
        <Migas tramos={[{ texto: 'Stock', href: '/stock' }, { texto: 'Cargar vehículo' }]} />
        <h1 className="mb-6 mt-4 text-2xl font-semibold tracking-tight">Cargar vehículo</h1>
        <EstadoVacio
          titulo="Todavía no hay sucursales"
          descripcion="Un vehículo se recibe en una sucursal. Abrí la primera desde la configuración de la agencia."
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl">
      <Migas tramos={[{ texto: 'Stock', href: '/stock' }, { texto: 'Cargar vehículo' }]} />

      <h1 className="mb-2 mt-4 text-2xl font-semibold tracking-tight">Cargar vehículo</h1>
      <p className="mb-6 text-sm text-neutro-texto">
        Entra <strong className="text-neutro-enfasis">en preparación</strong> y desde el stock se
        pasa a disponible cuando esté listo para publicar.{' '}
        <Link href="/stock" className="underline">
          Volver al stock
        </Link>
        .
      </p>

      <FormularioDeVehiculo sucursales={sucursales} marcas={marcas} />
    </div>
  );
}
