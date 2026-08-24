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

/**
 * Una peticion AUTENTICADA al backend.
 *
 * El token va tal cual como lo emitio Keycloak: el backend lo valida contra su
 * JWKS, asi que cualquier transformacion nuestra lo invalidaria.
 *
 * Sin cache: lo que devuelve depende de QUIEN pregunta. `RN-ST-12` hace que el
 * mismo vehiculo tenga 23 campos para un vendedor y 24 para un gerente —
 * cachear eso serviria la respuesta de uno al otro, que es una fuga de datos
 * disfrazada de optimizacion.
 */
export async function pedirConToken(ruta: string, token: string): Promise<unknown> {
  const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
    cache: 'no-store',
  });

  if (!respuesta.ok) {
    throw new ErrorDeApi(respuesta.status, ruta);
  }

  return respuesta.json();
}

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

/**
 * Una marca del catalogo de vehiculos.
 *
 * Catalogo cross-tenant: lo lee cualquiera y no lo escribe nadie. El backend lo
 * garantiza en la base, no en la aplicacion — ver la migracion `009`.
 */
export interface Marca {
  id: string;
  name: string;
  slug: string;
  origin_country: string | null;
}

/**
 * Un modelo, colgado de su marca.
 *
 * ⚠️ `year_to` en `null` significa QUE SE SIGUE VENDIENDO, no que falte el dato.
 * Son la misma ausencia de valor con significados opuestos, y por eso el campo
 * viaja siempre en vez de omitirse cuando esta vacio.
 */
export interface Modelo {
  id: string;
  brand_id: string;
  name: string;
  body_type: string;
  year_from: number;
  year_to: number | null;
}

function esMarca(valor: unknown): valor is Marca {
  if (typeof valor !== 'object' || valor === null) return false;
  const m = valor as Record<string, unknown>;

  return (
    typeof m.id === 'string' &&
    typeof m.name === 'string' &&
    typeof m.slug === 'string' &&
    (m.origin_country === null || typeof m.origin_country === 'string')
  );
}

function esModelo(valor: unknown): valor is Modelo {
  if (typeof valor !== 'object' || valor === null) return false;
  const m = valor as Record<string, unknown>;

  return (
    typeof m.id === 'string' &&
    typeof m.brand_id === 'string' &&
    typeof m.name === 'string' &&
    typeof m.body_type === 'string' &&
    typeof m.year_from === 'number' &&
    (m.year_to === null || typeof m.year_to === 'number')
  );
}

export async function obtenerMarcas(): Promise<Marca[]> {
  const datos = await pedir('/api/v1/catalog/brands');

  if (!Array.isArray(datos) || !datos.every(esMarca)) {
    throw new TypeError('El catalogo de marcas no tiene la forma esperada');
  }

  return datos;
}

/**
 * Los modelos de una marca, por su ID.
 *
 * ⚠️ EL BACKEND BUSCA POR ID, NO POR SLUG. Es lo que documenta el catalogo de
 * endpoints de `knowledge-base/02`, derivado de `spec-tecnica` (N1). El slug
 * queda del lado del frontend: las URLs legibles se resuelven con
 * `idDeMarcaPorSlug` contra el listado que la pagina ya tiene cargado, en vez de
 * pedirle al backend un contrato distinto del que su spec fija.
 *
 * Una marca inexistente da 404 y esto levanta `ErrorDeApi`, no una lista vacia:
 * "no hay modelos cargados" y "esa marca no existe" son cosas distintas y el
 * backend las distingue. Aplanarlas acá desharia esa distincion.
 */
export async function obtenerModelos(marcaId: string): Promise<Modelo[]> {
  const datos = await pedir(`/api/v1/catalog/brands/${encodeURIComponent(marcaId)}/models`);

  if (!Array.isArray(datos) || !datos.every(esModelo)) {
    throw new TypeError('El catalogo de modelos no tiene la forma esperada');
  }

  return datos;
}

/** Resuelve el slug de una URL contra las marcas ya cargadas. */
export function idDeMarcaPorSlug(marcas: readonly Marca[], slug: string): string | undefined {
  return marcas.find((marca) => marca.slug === slug)?.id;
}

// ── Stock ────────────────────────────────────────────────────────────────────

/**
 * Un vehiculo, como lo devuelven `GET /api/v1/vehicles` y `GET /vehicles/{id}`.
 *
 * LOS DOS ENDPOINTS RESPONDEN EL MISMO SCHEMA (`VehiculoSalida`), asi que hay un
 * solo tipo. Declarar un `VehiculoDetalle` aparte daria dos formas para un unico
 * contrato, y la que use menos pantallas es la que envejece sin que nadie mire.
 *
 * ⚠️ ESTA INTERFAZ DECLARA LOS 22 CAMPOS Y NO LOS QUE USA LA TABLA. Hasta la
 * ficha declaraba 11: el listado no necesitaba mas, y los otros once llegaban
 * por la red sin que TypeScript supiera que existian. Eso no es economia — es un
 * contrato a medias que obliga a redescubrir el schema cada vez que una pantalla
 * nueva necesita un campo. La lista de campos la vigila
 * `backend/tests/unit/test_vehiculo_espejado.py`.
 *
 * ⚠️ `acquisition_cost_ars` ES OPCIONAL A NIVEL DE TIPO, y eso no es laxitud:
 * es `RN-ST-12` en el sistema de tipos. El backend devuelve 23 campos a un
 * `salesperson` y 24 a un `manager` — la clave NO viene, no viene en `null`.
 *
 * Declararlo obligatorio obligaria a mentir con un `!` en cada uso; declararlo
 * opcional hace que TypeScript OBLIGUE a contemplar que no este, que es
 * exactamente la pregunta correcta.
 */
export interface Vehiculo {
  id: string;
  tenant_id: string;
  branch_id: string;
  assigned_user_id: string | null;
  domain_plate: string | null;
  chassis_number: string | null;
  brand_id: string;
  model_id: string;
  version_id: string | null;
  year: number;
  mileage_km: number;
  color: string;
  fuel_type: string;
  transmission: string;
  body_type: string;
  status: string;
  /** Decimal serializado como string. Ver el comentario de `Plan.price_ars`. */
  price_ars: string;
  price_usd: string | null;
  description: string | null;
  features: string[];
  /** ISO 8601, como lo serializa Pydantic. Se formatea en el momento de mostrar. */
  acquired_at: string | null;
  sold_at: string | null;
  created_at: string;
  /**
   * Solo para `manager` y `admin_staff` (`RN-ST-12`).
   *
   * ⚠️ AUSENTE Y `null` SIGNIFICAN COSAS DISTINTAS, y la diferencia importa:
   *
   *   - la clave NO ESTA  -> tu rol no puede verlo
   *   - la clave es `null` -> podes verlo, y este vehiculo no lo tiene cargado
   *
   * Por eso el tipo admite los dos y quien decide si mostrar la columna
   * pregunta por la PRESENCIA de la clave, no por su valor.
   */
  acquisition_cost_ars?: string | null;
}

function esVehiculo(valor: unknown): valor is Vehiculo {
  if (typeof valor !== 'object' || valor === null) return false;
  const v = valor as Record<string, unknown>;

  return (
    typeof v.id === 'string' &&
    typeof v.tenant_id === 'string' &&
    typeof v.branch_id === 'string' &&
    (v.assigned_user_id === null || typeof v.assigned_user_id === 'string') &&
    (v.domain_plate === null || typeof v.domain_plate === 'string') &&
    (v.chassis_number === null || typeof v.chassis_number === 'string') &&
    typeof v.brand_id === 'string' &&
    typeof v.model_id === 'string' &&
    (v.version_id === null || typeof v.version_id === 'string') &&
    typeof v.year === 'number' &&
    typeof v.mileage_km === 'number' &&
    typeof v.color === 'string' &&
    typeof v.fuel_type === 'string' &&
    typeof v.transmission === 'string' &&
    typeof v.body_type === 'string' &&
    typeof v.status === 'string' &&
    typeof v.price_ars === 'string' &&
    (v.price_usd === null || typeof v.price_usd === 'string') &&
    (v.description === null || typeof v.description === 'string') &&
    Array.isArray(v.features) &&
    (v.acquired_at === null || typeof v.acquired_at === 'string') &&
    (v.sold_at === null || typeof v.sold_at === 'string') &&
    typeof v.created_at === 'string' &&
    // El costo NO se exige. Su ausencia es el caso normal para un vendedor, y
    // `null` el de un gerente mirando un vehiculo sin costo cargado.
    (v.acquisition_cost_ars === undefined ||
      v.acquisition_cost_ars === null ||
      typeof v.acquisition_cost_ars === 'string')
  );
}

/**
 * El stock de la agencia del token.
 *
 * ⚠️ RECORRE TODAS LAS PAGINAS — C-15, `T-080`, `design.md` D-2. Desde ese
 * change `GET /vehicles` dejo de devolver TODO el stock: pagina por cursor,
 * 20 vehiculos por defecto, con la pagina siguiente indicada en el header
 * `X-Next-Cursor` (su ausencia es la ultima pagina). El CUERPO de cada
 * pagina sigue siendo un array — eso es lo que `esVehiculo` sigue validando
 * sin cambios — asi que lo unico nuevo acá es EL LOOP que las junta.
 *
 * Esta funcion sigue devolviendo la lista COMPLETA a proposito: la
 * paginacion de la UI es **C-19**, todavia no existe, y truncar en 20 sin
 * avisar seria peor que el problema que este change vino a cerrar — una
 * agencia con mas de 20 autos veria solo los primeros 20 en la pantalla de
 * stock, sin ningun error.
 */
export async function obtenerVehiculos(token: string): Promise<Vehiculo[]> {
  const vehiculos: Vehiculo[] = [];
  let cursor: string | null = null;

  do {
    const ruta: string = cursor
      ? `/api/v1/vehicles?cursor=${encodeURIComponent(cursor)}`
      : '/api/v1/vehicles';
    const respuesta = await fetch(`${API_BASE_URL}${ruta}`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });

    if (!respuesta.ok) {
      throw new ErrorDeApi(respuesta.status, ruta);
    }

    const datos: unknown = await respuesta.json();
    if (!Array.isArray(datos) || !datos.every(esVehiculo)) {
      throw new TypeError('El listado de vehiculos no tiene la forma esperada');
    }

    vehiculos.push(...datos);
    cursor = respuesta.headers.get('X-Next-Cursor');
  } while (cursor !== null);

  return vehiculos;
}

/**
 * Un vehiculo de la agencia del token, por su id.
 *
 * ⚠️ UN VEHICULO DE OTRA AGENCIA DA 404, NO 403, y esa es la respuesta correcta:
 * la politica RLS hace que para esta sesion la fila no exista. Un 403 confirmaria
 * que el id es real y le diria a quien pruebe ids al azar cuales estan tomados;
 * un 404 no distingue "no existe" de "no es tuyo", que es justo lo que se quiere.
 *
 * El 404 se propaga como `ErrorDeApi` con `estado === 404`. La pagina lo traduce
 * a `notFound()`; no se aplana acá a `null`, porque "no esta" y "el backend se
 * cayo" tienen que poder distinguirse en el llamador.
 */
export async function obtenerVehiculo(id: string, token: string): Promise<Vehiculo> {
  const datos = await pedirConToken(`/api/v1/vehicles/${encodeURIComponent(id)}`, token);

  if (!esVehiculo(datos)) {
    throw new TypeError('El vehiculo no tiene la forma esperada');
  }

  return datos;
}

/**
 * Las marcas del catalogo, indexadas por id.
 *
 * El listado de vehiculos trae `brand_id` y no el nombre. Se resuelve acá y no
 * pidiendo un endpoint por vehiculo: son 40 marcas para todo el sistema y el
 * catalogo es cross-tenant, asi que una sola llamada alcanza para cualquier
 * cantidad de filas.
 */
export async function obtenerMarcasPorId(): Promise<ReadonlyMap<string, string>> {
  // Reusa `obtenerMarcas` en vez de repetir el fetch y el estrechamiento: una
  // segunda copia de la validacion es una segunda copia que envejece.
  const marcas = await obtenerMarcas();
  return new Map(marcas.map((marca) => [marca.id, marca.name]));
}

// ── Sucursales ──────────────────────────────────────────────────────────────

/**
 * Una sucursal de la agencia del token.
 *
 * `tenant_id` viene en la salida a proposito y no es una fuga: el cliente solo
 * recibe lo suyo, que es lo que garantiza la politica RLS. Lo que nunca se
 * acepta es en la ENTRADA (regla dura 1).
 */
export interface Sucursal {
  id: string;
  tenant_id: string;
  name: string;
  city: string;
  province: string;
  address: string | null;
  phone: string | null;
  is_active: boolean;
  created_at: string;
}

function esSucursal(valor: unknown): valor is Sucursal {
  if (typeof valor !== 'object' || valor === null) return false;
  const s = valor as Record<string, unknown>;

  return (
    typeof s.id === 'string' &&
    typeof s.tenant_id === 'string' &&
    typeof s.name === 'string' &&
    typeof s.city === 'string' &&
    typeof s.province === 'string' &&
    typeof s.is_active === 'boolean' &&
    typeof s.created_at === 'string' &&
    (s.address === null || typeof s.address === 'string') &&
    (s.phone === null || typeof s.phone === 'string')
  );
}

/**
 * TODAS las sucursales de la agencia del token, activas y dadas de baja.
 *
 * Es lo que el backend devuelve, sin filtrar. Existe porque la ficha de un
 * vehiculo tiene que poder nombrar la sucursal donde esta —y esa sucursal puede
 * estar dada de baja, porque el soft delete universal (principio 3) la conserva—.
 * Filtrarla acá dejaria la ficha mostrando un guion en vez del nombre, que es
 * peor que nombrar una sucursal cerrada.
 *
 * El comentario de `obtenerSucursales` ya anticipaba este caso: decia que una
 * sucursal de baja "hace falta para mostrar el historial de un vehiculo que
 * estuvo ahi". Esta es esa necesidad, y por eso el filtro se movio afuera en vez
 * de agregarle un booleano a la funcion.
 */
export async function obtenerTodasLasSucursales(token: string): Promise<Sucursal[]> {
  const datos = await pedirConToken('/api/v1/branches', token);

  if (!Array.isArray(datos) || !datos.every(esSucursal)) {
    throw new TypeError('El listado de sucursales no tiene la forma esperada');
  }

  return datos;
}

/**
 * Las sucursales ACTIVAS de la agencia del token.
 *
 * El filtro de `is_active` es de esta funcion y no del backend: una sucursal dada
 * de baja sigue existiendo, pero lo que no puede es RECIBIR un vehiculo nuevo, y
 * este listado alimenta justamente ese desplegable.
 */
export async function obtenerSucursales(token: string): Promise<Sucursal[]> {
  return (await obtenerTodasLasSucursales(token)).filter((sucursal) => sucursal.is_active);
}
