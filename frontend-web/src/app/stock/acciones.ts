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

export interface Resultado {
  ok: boolean;
  mensaje: string;
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
