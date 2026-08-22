'use server';

/**
 * Acciones de servidor del stock.
 *
 * Corren en el proceso de Next, con el token de la sesión. El navegador no ve
 * la URL del backend ni el token por este camino, y CORS no interviene.
 *
 * NINGUNA DE ESTAS FUNCIONES DECIDE PERMISOS. Mandan la petición y traducen la
 * respuesta. Quién puede hacer qué lo decide `rbac.py` del backend, y esa es la
 * única copia de la matriz que existe.
 */

import { revalidatePath } from 'next/cache';

import { auth } from '@/auth';
import { API_BASE_URL } from '@/lib/api';
import { mensajeDeAlta, type CuerpoDeAlta } from '@/lib/vehiculo-nuevo';

export interface Resultado {
  ok: boolean;
  mensaje: string;
}

/** El alta devuelve ademas el id, que es lo unico util que trae el 201. */
export interface ResultadoDeAlta extends Resultado {
  id?: string;
}

/**
 * Los rechazos que este endpoint puede dar, en castellano.
 *
 * Se traduce por CODIGO y no por estado HTTP. Los tres 403 —`insufficient_permission`,
 * `out_of_scope` y `transition_not_allowed`— mandan al usuario por caminos
 * distintos: pedirle el permiso a un gerente, pedir que te asignen el vehículo,
 * o pedirle a otro rol que haga el cambio. Colapsarlos en "no tenés permiso"
 * deja a las tres personas sin saber qué hacer.
 *
 * ⚠️ LOS CODIGOS SE VERIFICARON CONTRA EL BACKEND CORRIENDO, no se dedujeron.
 * La primera versión tenía `invalid_transition`, que **el backend nunca manda**:
 * una transición ilegal para todos sale como `domain_error`. Ese mensaje no se
 * habría mostrado jamás, y nadie lo habría notado — el fallback genérico se ve
 * razonable.
 */
const MENSAJES = {
  not_authenticated: 'Tu sesión venció. Volvé a iniciar sesión.',
  insufficient_permission: 'Tu rol no puede cambiar el estado de un vehículo.',
  out_of_scope: 'Ese vehículo no está asignado a vos.',
  transition_not_allowed: 'Tu rol no puede hacer ese cambio de estado.',
  // `RN-ST-05`: la transición no existe para nadie, ni para el gerente.
  domain_error: 'Ese cambio de estado no existe para ningún rol.',
  // El cuerpo no pasó la validación. Hoy el caso típico es vender sin razón
  // (`RN-ST-06`), que este botón no puede completar por sí solo.
  validation_error: 'Falta algún dato para ese cambio. Vender exige una razón.',
} as const;

/** El mensaje de un codigo, o `null` si el backend mando uno que no conocemos. */
function mensajeDe(codigo: string): string | null {
  return codigo in MENSAJES ? MENSAJES[codigo as keyof typeof MENSAJES] : null;
}

export async function cambiarEstado(vehiculoId: string, destino: string): Promise<Resultado> {
  const sesion = await auth();

  if (!sesion?.accessToken) {
    return { ok: false, mensaje: MENSAJES.not_authenticated };
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE_URL}/api/v1/vehicles/${vehiculoId}/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sesion.accessToken}`,
      },
      body: JSON.stringify({ status: destino }),
      cache: 'no-store',
    });
  } catch (error) {
    // Ver el comentario del `catch` de la página: el usuario ve el cartel, el
    // log ve la causa.
    console.error('[stock] no se pudo cambiar el estado:', error);
    return { ok: false, mensaje: 'El servicio no respondió. Intentá de nuevo.' };
  }

  if (respuesta.ok) {
    // Sin esto la tabla sigue mostrando el estado viejo hasta que alguien
    // recargue a mano: el render es del servidor y su caché no sabe que el dato
    // cambió por una acción.
    revalidatePath('/stock');
    // LA FICHA TAMBIÉN, y no es redundante: los mismos botones viven en las dos
    // pantallas. Revalidar solo el listado dejaba la ficha mostrando el estado
    // viejo —con los botones de la transición ya hecha— hasta recargar a mano.
    // Se revalida la RUTA y no el id concreto: `revalidatePath` con un segmento
    // dinámico alcanza a todas sus instancias, que es lo que se quiere cuando la
    // misma acción se dispara desde la fila de una tabla.
    revalidatePath('/stock/[id]', 'page');
    return { ok: true, mensaje: 'Estado actualizado.' };
  }

  const cuerpo: unknown = await respuesta.json().catch(() => null);
  const codigo =
    typeof cuerpo === 'object' && cuerpo !== null && 'code' in cuerpo
      ? String((cuerpo as { code: unknown }).code)
      : '';

  console.error(`[stock] el backend rechazo el cambio: ${respuesta.status} ${codigo}`);

  return {
    ok: false,
    mensaje: mensajeDe(codigo) ?? `El backend rechazó el cambio (${respuesta.status}).`,
  };
}

/**
 * El alta de un vehículo.
 *
 * Recibe el cuerpo YA armado por `aCuerpo`, no el borrador del formulario: la
 * conversión y la validación son lógica pura y viven en `lib/vehiculo-nuevo.ts`,
 * donde se pueden probar sin montar Next ni NextAuth. Acá solo queda mandar la
 * petición y traducir la respuesta.
 *
 * NO decide permisos, igual que `cambiarEstado`. Un `salesperson` puede llegar
 * hasta acá y recibir 403 — verificado en vivo—, y eso es lo correcto: la única
 * copia de la matriz que existe es `rbac.py`.
 */
export async function crearVehiculo(cuerpo: CuerpoDeAlta): Promise<ResultadoDeAlta> {
  const sesion = await auth();

  if (!sesion?.accessToken) {
    return { ok: false, mensaje: MENSAJES.not_authenticated };
  }

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE_URL}/api/v1/vehicles`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${sesion.accessToken}`,
      },
      body: JSON.stringify(cuerpo),
      cache: 'no-store',
    });
  } catch (error) {
    console.error('[stock] no se pudo cargar el vehiculo:', error);
    return { ok: false, mensaje: 'El servicio no respondió. Intentá de nuevo.' };
  }

  if (respuesta.status === 201) {
    // La tabla del stock se renderiza en el servidor y su caché no sabe que
    // apareció una fila. Sin esto el vehículo recién cargado no aparece hasta
    // que alguien recargue a mano, y el usuario vuelve a cargarlo.
    revalidatePath('/stock');

    const creado: unknown = await respuesta.json().catch(() => null);
    const id =
      typeof creado === 'object' && creado !== null && 'id' in creado
        ? String((creado as { id: unknown }).id)
        : undefined;

    return { ok: true, mensaje: 'Vehículo cargado.', id };
  }

  const cuerpoDelError: unknown = await respuesta.json().catch(() => null);
  const codigo =
    typeof cuerpoDelError === 'object' && cuerpoDelError !== null && 'code' in cuerpoDelError
      ? String((cuerpoDelError as { code: unknown }).code)
      : '';

  console.error(`[stock] el backend rechazo el alta: ${respuesta.status} ${codigo}`);

  return {
    ok: false,
    mensaje:
      mensajeDeAlta(codigo, respuesta.status) ??
      `El backend rechazó el alta (${respuesta.status}).`,
  };
}
