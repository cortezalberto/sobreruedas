/**
 * `obtenerSucursales` valida lo que recibe, como el resto de `lib/api.ts`.
 *
 * El alta de un vehículo exige `branch_id`, y el usuario lo elige de un
 * desplegable. Si el guarda de tipo dejara pasar una fila sin `id`, el
 * desplegable ofrecería una opción con `value=undefined` y el POST saldría con
 * `branch_id` vacío — un 422 que parece del formulario y viene del catálogo.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ErrorDeApi, obtenerSucursales, obtenerTodasLasSucursales } from '@/lib/api';

const SUCURSAL_VALIDA = {
  id: '22222222-2222-2222-2222-222222222222',
  tenant_id: '11111111-1111-1111-1111-111111111111',
  name: 'Casa central',
  city: 'Mendoza',
  province: 'Mendoza',
  address: null,
  phone: null,
  is_active: true,
  created_at: '2026-08-19T01:16:04.198009Z',
};

function responderCon(cuerpo: unknown, estado = 200): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(cuerpo), { status: estado })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('obtenerSucursales', () => {
  it('devuelve las sucursales cuando la respuesta tiene la forma esperada', async () => {
    responderCon([SUCURSAL_VALIDA]);

    const sucursales = await obtenerSucursales('un-token');

    expect(sucursales).toHaveLength(1);
    expect(sucursales[0]?.name).toBe('Casa central');
  });

  it('manda el token en la cabecera', async () => {
    // Sin `Authorization` el backend responde 401 y la pantalla diría "no se
    // pudo cargar" sin que nadie sepa que faltaba el token.
    const espia = vi.fn(async () => new Response(JSON.stringify([SUCURSAL_VALIDA])));
    vi.stubGlobal('fetch', espia);

    await obtenerSucursales('un-token');

    const llamada = espia.mock.calls[0] as unknown as [string, RequestInit];
    const cabeceras = llamada[1].headers as Record<string, string>;
    expect(cabeceras.Authorization).toBe('Bearer un-token');
  });

  it('rechaza una fila a la que le falta el nombre', async () => {
    const incompleta: Record<string, unknown> = { ...SUCURSAL_VALIDA };
    delete incompleta.name;
    responderCon([incompleta]);

    await expect(obtenerSucursales('un-token')).rejects.toThrow(TypeError);
  });

  it('propaga el error de la API cuando el backend rechaza', async () => {
    responderCon({ code: 'insufficient_permission' }, 403);

    await expect(obtenerSucursales('un-token')).rejects.toThrow(ErrorDeApi);
  });

  it('deja afuera las sucursales dadas de baja', async () => {
    // Una sucursal inactiva sigue existiendo —soft delete universal, principio
    // 3— pero no se puede recibir un vehículo en ella. Ofrecerla en el
    // desplegable sería ofrecer un destino que el backend va a rechazar.
    responderCon([SUCURSAL_VALIDA, { ...SUCURSAL_VALIDA, id: 'otra', is_active: false }]);

    const sucursales = await obtenerSucursales('un-token');

    expect(sucursales).toHaveLength(1);
  });
});

describe('obtenerTodasLasSucursales', () => {
  it('conserva las dadas de baja — la ficha tiene que poder nombrarlas', () => {
    // El complemento exacto del test de arriba, y la razon por la que el filtro
    // se movio afuera de la funcion. Un vehiculo puede estar en una sucursal
    // cerrada: el soft delete la conserva justamente para eso. Si la ficha
    // pidiera el listado filtrado, mostraria un guion donde hay un nombre.
    responderCon([SUCURSAL_VALIDA, { ...SUCURSAL_VALIDA, id: 'otra', is_active: false }]);

    return expect(obtenerTodasLasSucursales('un-token')).resolves.toHaveLength(2);
  });

  it('valida igual que la version filtrada', () => {
    // El filtro se movio, el guarda de tipo NO. Sin este test, sacar la
    // validacion de la funcion nueva pasaria en verde: la vieja la sigue
    // teniendo por delegacion, pero la nueva es la que usa la ficha.
    const sinNombre: Record<string, unknown> = { ...SUCURSAL_VALIDA };
    delete sinNombre.name;
    responderCon([sinNombre]);

    return expect(obtenerTodasLasSucursales('un-token')).rejects.toThrow(TypeError);
  });
});
