/**
 * El guarda de tipo del vehículo, que hasta la ficha no tenía ninguno.
 *
 * `obtenerVehiculos` existe desde la pantalla de stock y `esVehiculo` nunca se
 * probó: el listado andaba, así que nadie lo notó. Cuando la ficha extendió la
 * interfaz de 11 campos a 23, el guarda pasó a exigir doce campos más — y un
 * guarda más estricto sin tests es la forma más fácil de romper una pantalla que
 * funcionaba. Estos tests son la red que faltaba, no un extra de la ficha.
 *
 * LOS 23 CAMPOS SALEN DE `VehiculoSalida`, no de lo que la pantalla usa. Que la
 * lista coincida con la del backend lo vigila
 * `backend/tests/unit/test_vehiculo_espejado.py`; acá se prueba que el guarda
 * haga algo con ella.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { ErrorDeApi, obtenerVehiculo, obtenerVehiculos } from '@/lib/api';

import { vehiculo } from '../fixtures/vehiculo';

const VEHICULO_VALIDO = vehiculo();

function responderCon(cuerpo: unknown, estado = 200): void {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(cuerpo), { status: estado })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('obtenerVehiculos', () => {
  it('devuelve el listado cuando la respuesta tiene la forma esperada', async () => {
    responderCon([VEHICULO_VALIDO]);

    const stock = await obtenerVehiculos('un-token');

    expect(stock).toHaveLength(1);
    expect(stock[0]?.domain_plate).toBe('AB123CD');
  });

  it('rechaza una fila a la que le falta uno de los campos nuevos', async () => {
    // `fuel_type` es de los doce que la interfaz no declaraba hasta la ficha.
    // Sin este test, un guarda que se olvidara de exigirlo pasaría en verde y la
    // ficha mostraría "undefined" donde va el combustible.
    const incompleto: Record<string, unknown> = { ...VEHICULO_VALIDO };
    delete incompleto.fuel_type;
    responderCon([incompleto]);

    await expect(obtenerVehiculos('un-token')).rejects.toThrow(TypeError);
  });

  it('rechaza un `features` que no es arreglo', async () => {
    // La ficha hace `features.map(...)`. Si el backend mandara `null` —o un
    // string— el `.map` reventaría en el render del servidor, que es un 500 y no
    // un cartel. El guarda lo convierte en un error del cliente, con causa.
    responderCon([{ ...VEHICULO_VALIDO, features: null }]);

    await expect(obtenerVehiculos('un-token')).rejects.toThrow(TypeError);
  });

  it('acepta que falte `acquisition_cost_ars` — es el caso normal de un rol sin costo', async () => {
    // `RN-ST-12`. Exigir el costo rompería el listado para el rol que más lo usa.
    expect('acquisition_cost_ars' in VEHICULO_VALIDO).toBe(false);
    responderCon([VEHICULO_VALIDO]);

    await expect(obtenerVehiculos('un-token')).resolves.toHaveLength(1);
  });
});

describe('obtenerVehiculo', () => {
  it('devuelve el vehículo cuando la respuesta tiene la forma esperada', async () => {
    responderCon(VEHICULO_VALIDO);

    const encontrado = await obtenerVehiculo(VEHICULO_VALIDO.id, 'un-token');

    expect(encontrado.color).toBe('Blanco');
  });

  it('manda el token y pide el id en la ruta', async () => {
    responderCon(VEHICULO_VALIDO);

    await obtenerVehiculo(VEHICULO_VALIDO.id, 'un-token');

    const llamada = vi.mocked(fetch).mock.calls[0];
    expect(String(llamada?.[0])).toContain(`/api/v1/vehicles/${VEHICULO_VALIDO.id}`);
    expect(llamada?.[1]?.headers).toMatchObject({ Authorization: 'Bearer un-token' });
  });

  it('propaga el 404 como `ErrorDeApi` y NO como lista vacía ni `null`', async () => {
    // La página lo traduce a `notFound()`. Si esto devolviera `null`, la ficha no
    // podría distinguir "ese vehículo no existe" de "el backend se cayó", y las
    // dos terminarían en el mismo cartel equivocado.
    //
    // El 404 tapa tres casos distintos a propósito: id inventado, vehículo dado
    // de baja, y vehículo de OTRA agencia —que para esta sesión no existe porque
    // la política RLS lo esconde—. Un 403 en el tercero confirmaría que el id es
    // real.
    responderCon({ code: 'not_found' }, 404);

    await expect(obtenerVehiculo('cualquiera', 'un-token')).rejects.toMatchObject({
      name: 'ErrorDeApi',
      estado: 404,
    });
  });

  it('propaga los otros errores del backend', async () => {
    responderCon({ code: 'insufficient_permission' }, 403);

    await expect(obtenerVehiculo('cualquiera', 'un-token')).rejects.toThrow(ErrorDeApi);
  });

  it('rechaza una respuesta con forma inesperada', async () => {
    responderCon({ id: 'solo-el-id' });

    await expect(obtenerVehiculo('cualquiera', 'un-token')).rejects.toThrow(TypeError);
  });

  it('rechaza un arreglo donde espera un objeto', async () => {
    // El endpoint del listado y el del detalle se diferencian por un segmento de
    // la ruta. Un error de armado devolvería la lista entera acá, y sin esto el
    // guarda podría dejarla pasar como "algo que no es null".
    responderCon([VEHICULO_VALIDO]);

    await expect(obtenerVehiculo('cualquiera', 'un-token')).rejects.toThrow(TypeError);
  });
});
