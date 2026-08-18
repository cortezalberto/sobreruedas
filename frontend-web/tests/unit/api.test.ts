/**
 * El cliente del backend valida lo que recibe.
 *
 * POR QUE HAY UN GUARDA DE TIPO Y NO UN `as Plan`. `respuesta.json()` devuelve
 * `any`, y un `as Plan` le dice a TypeScript que confie sin verificar nada. Ese
 * es el agujero exacto por el que un cambio de contrato del backend —un campo
 * renombrado, un numero que pasa a string— llega hasta un `.map()` en un
 * componente y revienta en la pantalla del cliente, no en CI.
 *
 * La regla dura 7 prohibe `any` justamente por esto. Estos tests fijan que el
 * estrechamiento sirva para algo: sin ellos, un guarda que devuelva `true`
 * siempre pasaria igual de desapercibido.
 */
import { describe, expect, it, vi, afterEach } from 'vitest';

import {
  ErrorDeApi,
  idDeMarcaPorSlug,
  obtenerMarcas,
  obtenerModelos,
  obtenerPlanes,
  SIN_TECHO,
} from '@/lib/api';

const PLAN_VALIDO = {
  id: '11111111-1111-1111-1111-111111111111',
  code: 'starter',
  name: 'Starter',
  price_ars: '45000.00',
  max_users: 2,
  max_vehicles: 80,
  max_branches: 1,
  max_whatsapp_messages_month: 1000,
  modules: ['stock', 'crm'],
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

describe('obtenerPlanes', () => {
  it('devuelve los planes cuando la respuesta tiene la forma esperada', async () => {
    responderCon([PLAN_VALIDO]);

    const planes = await obtenerPlanes();

    const [primero] = planes;
    expect(planes).toHaveLength(1);
    expect(primero?.code).toBe('starter');
  });

  it('rechaza una respuesta a la que le falta un campo', async () => {
    const incompleto: Record<string, unknown> = { ...PLAN_VALIDO };
    delete incompleto.max_vehicles;
    responderCon([incompleto]);

    await expect(obtenerPlanes()).rejects.toThrow(TypeError);
  });

  it('rechaza un precio que llega como numero en vez de string', async () => {
    // No es quisquillosidad: en punto flotante 45000.10 no es 45000.10, y un
    // precio que se redondea solo es un problema de facturacion, no de tipos.
    responderCon([{ ...PLAN_VALIDO, price_ars: 45000 }]);

    await expect(obtenerPlanes()).rejects.toThrow(TypeError);
  });

  it('rechaza una respuesta que no es una lista', async () => {
    responderCon({ planes: [PLAN_VALIDO] });

    await expect(obtenerPlanes()).rejects.toThrow(TypeError);
  });

  it('levanta ErrorDeApi con el estado cuando el backend falla', async () => {
    responderCon({ detail: 'roto' }, 503);

    await expect(obtenerPlanes()).rejects.toThrow(ErrorDeApi);
  });

  it('deja pasar el cero de los limites sin techo', async () => {
    // Enterprise tiene `max_vehicles = 0`, que significa SIN TECHO. Un guarda
    // escrito con `typeof p.max_vehicles === 'number' && p.max_vehicles` lo
    // rechazaria por falsy, y el plan mas caro del producto dejaria de cargar.
    responderCon([{ ...PLAN_VALIDO, code: 'enterprise', max_vehicles: SIN_TECHO }]);

    const planes = await obtenerPlanes();

    const [enterprise] = planes;
    expect(enterprise?.max_vehicles).toBe(0);
  });
});

const MARCA_VALIDA = {
  id: '22222222-2222-2222-2222-222222222222',
  name: 'Toyota',
  slug: 'toyota',
  origin_country: 'Japón',
};

const MODELO_VALIDO = {
  id: '33333333-3333-3333-3333-333333333333',
  brand_id: MARCA_VALIDA.id,
  name: 'Hilux',
  body_type: 'pickup',
  year_from: 2016,
  year_to: null,
};

describe('obtenerMarcas', () => {
  it('acepta una marca sin pais de origen', () => {
    // `origin_country` es nullable en la base. Un guarda que exigiera string
    // dejaria afuera marcas validas.
    responderCon([{ ...MARCA_VALIDA, origin_country: null }]);

    return expect(obtenerMarcas()).resolves.toHaveLength(1);
  });

  it('rechaza una marca sin slug', async () => {
    const incompleta: Record<string, unknown> = { ...MARCA_VALIDA };
    delete incompleta.slug;
    responderCon([incompleta]);

    await expect(obtenerMarcas()).rejects.toThrow(TypeError);
  });
});

describe('obtenerModelos', () => {
  it('deja pasar year_to nulo, que significa vigente', async () => {
    responderCon([MODELO_VALIDO]);

    const [modelo] = await obtenerModelos(MARCA_VALIDA.id);

    expect(modelo?.year_to).toBeNull();
  });

  it('acepta un modelo discontinuado', async () => {
    responderCon([{ ...MODELO_VALIDO, year_to: 2020 }]);

    const [modelo] = await obtenerModelos(MARCA_VALIDA.id);

    expect(modelo?.year_to).toBe(2020);
  });

  it('propaga el 404 como ErrorDeApi y no como lista vacia', async () => {
    // El backend distingue "marca inexistente" de "marca sin modelos". Aplanar
    // las dos en `[]` desharia esa distincion justo del lado que la muestra.
    responderCon({ detail: 'no existe' }, 404);

    await expect(obtenerModelos('00000000-0000-0000-0000-000000000000')).rejects.toThrow(
      ErrorDeApi,
    );
  });

  it('escapa el slug en la URL', async () => {
    // Se captura la URL en vez de leerla de `mock.calls`: sin un parametro
    // declarado, `calls` es una tupla vacia y TypeScript no deja indexarla.
    let urlPedida = '';
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        urlPedida = url;
        return new Response('[]', { status: 200 });
      }),
    );

    await obtenerModelos('a/b');

    expect(urlPedida).toContain('a%2Fb');
    expect(urlPedida).toContain('/api/v1/catalog/brands/');
  });
});

describe('idDeMarcaPorSlug', () => {
  it('resuelve el slug de la URL contra las marcas cargadas', () => {
    // El backend busca por id; el slug vive solo en las URLs del frontend.
    expect(idDeMarcaPorSlug([MARCA_VALIDA], 'toyota')).toBe(MARCA_VALIDA.id);
  });

  it('devuelve undefined si el slug no existe, para que la pagina de 404', () => {
    expect(idDeMarcaPorSlug([MARCA_VALIDA], 'ferrari')).toBeUndefined();
  });
});
