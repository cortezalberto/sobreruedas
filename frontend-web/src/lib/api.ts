/**
 * Cliente HTTP del backend.
 *
 * LA URL SALE DEL ENTORNO Y NO DEL CODIGO. `NEXT_PUBLIC_API_BASE_URL` es una de
 * las 36 variables de `ADR-013`, y el default de `.env.example` es el puerto
 * 8000. En una maquina donde el backend escuche en otro puerto va en
 * `.env.local`, que esta gitignoreado — hardcodear el puerto de una maquina en
 * el codigo rompe el de todas las demas.
 *
 * SIN `any`. Regla dura 7: lo que entra por la red es `unknown` hasta que se
 * estrecha. `fetch` devuelve `any` desde `.json()`, y ese es exactamente el
 * agujero por donde un cambio de contrato del backend llega hasta un `.map()`
 * en un componente sin que TypeScript diga nada.
 */

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export class ErrorDeApi extends Error {
  constructor(
    readonly estado: number,
    readonly ruta: string,
  ) {
    super(`El backend respondio ${estado} en ${ruta}`);
    this.name = 'ErrorDeApi';
  }
}

/**
 * Un plan del catalogo comercial.
 *
 * ⚠️ En los limites, `0` significa SIN TECHO — no "cero permitidos". Es la
 * convencion de `spec-tecnica` 3.3 y viaja tal cual desde el backend, que tiene
 * un test dedicado a que no se traduzca a `null`. Mostrar "0 vehiculos" en
 * Enterprise es el error que esta convencion existe para evitar.
 */
export interface Plan {
  id: string;
  code: string;
  name: string;
  /** Decimal serializado como string: en punto flotante 45000.10 no es 45000.10. */
  price_ars: string;
  max_users: number;
  max_vehicles: number;
  max_branches: number;
  max_whatsapp_messages_month: number;
  modules: string[];
}

export const SIN_TECHO = 0;

async function pedir(ruta: string): Promise<unknown> {
  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    headers: { Accept: 'application/json' },
    // El catalogo cambia cuando cambia la grilla comercial, no entre pedidos.
    // 60 s alcanza para no golpear la base en cada carga y es lo bastante corto
    // para que una correccion de precio se vea en el minuto.
    next: { revalidate: 60 },
  });

  if (!respuesta.ok) {
    throw new ErrorDeApi(respuesta.status, ruta);
  }

  return respuesta.json();
}

function esPlan(valor: unknown): valor is Plan {
  if (typeof valor !== 'object' || valor === null) return false;
  const p = valor as Record<string, unknown>;

  return (
    typeof p.id === 'string' &&
    typeof p.code === 'string' &&
    typeof p.name === 'string' &&
    typeof p.price_ars === 'string' &&
    typeof p.max_users === 'number' &&
    typeof p.max_vehicles === 'number' &&
    typeof p.max_branches === 'number' &&
    typeof p.max_whatsapp_messages_month === 'number' &&
    Array.isArray(p.modules)
  );
}

export async function obtenerPlanes(): Promise<Plan[]> {
  const datos = await pedir('/api/v1/plans');

  if (!Array.isArray(datos) || !datos.every(esPlan)) {
    throw new TypeError('El catalogo de planes no tiene la forma esperada');
  }

  return datos;
}
