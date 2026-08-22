/**
 * Decisiones de presentación del stock, SIN dependencias de framework.
 *
 * Vive en `lib/` y no en `app/stock/page.tsx` por un motivo concreto: esa
 * página importa `@/auth`, que arrastra NextAuth y con él `next/server`. Un
 * test que quiera probar esta lógica en jsdom no puede montar nada de eso.
 *
 * Es la segunda vez que aparece lo mismo en este change —la primera fue
 * `Encabezado` con `<Sesion />` adentro—, así que queda escrito: lo que se
 * pueda probar solo, va donde se pueda probar solo.
 */
import { ErrorDeApi, type Vehiculo } from '@/lib/api';
import type { Opcion } from '@/lib/vehiculo-nuevo';

/**
 * Si el backend mandó el costo — que es lo mismo que "este rol puede verlo".
 *
 * Se pregunta por la PRESENCIA de la clave, NO por su valor ni por el rol:
 *
 *   - clave ausente   -> `RN-ST-12`, este rol no lo ve
 *   - clave en `null` -> lo ve, y este vehículo no lo tiene cargado
 *
 * Preguntar `!== undefined` escondería la columna a un gerente cuyo stock
 * todavía no tiene costos, que es justo el estado de una agencia que recién
 * carga sus autos. Y preguntar por el rol sería una segunda copia de la matriz
 * de permisos — la del cliente, que se edita con las herramientas del navegador.
 */
export function elBackendMandaElCosto(vehiculos: readonly Vehiculo[]): boolean {
  return vehiculos.some((vehiculo) => 'acquisition_cost_ars' in vehiculo);
}

/** Las columnas de la tabla, con la de costo solo si corresponde. */
export function columnasPara(vehiculos: readonly Vehiculo[]): string[] {
  return [
    'Dominio',
    'Marca',
    'Año',
    'Color',
    'Kilómetros',
    'Precio',
    ...(elBackendMandaElCosto(vehiculos) ? ['Costo'] : []),
    'Estado',
    'Cambiar a',
  ];
}

/**
 * Las transiciones que `RN-ST-05` admite, copiadas del backend.
 *
 * ⚠️ ESTO SE COPIA Y LA MATRIZ DE PERMISOS NO, y la diferencia es la que fija
 * `ADR-034`:
 *
 *   - QUE transiciones existen es conocimiento de DOMINIO. Un auto no pasa de
 *     "en preparación" a "vendido" para nadie, ni para el gerente. Reflejarlo
 *     acá es lo que permite ofrecer botones que tengan sentido.
 *
 *   - QUIEN puede hacer cada una es la matriz de permisos, y **no se copia**.
 *     Un `salesperson` solo pasa `available` -> `reserved`, y eso lo decide el
 *     backend: la UI ofrece la transición y si no le corresponde recibe 403.
 *
 * Copiar la matriz daría una segunda fuente de verdad sobre permisos, editable
 * desde el navegador. Copiar la máquina de estados da, en el peor caso, un
 * botón de más que el backend rechaza — visible y sin consecuencia.
 *
 * La deriva es real igual: si el backend agrega una transición y esto no, el
 * botón no aparece. Es la dirección segura de las dos.
 */
export const TRANSICIONES: ReadonlyMap<string, readonly string[]> = new Map([
  ['in_preparation', ['available']],
  ['available', ['reserved', 'in_workshop', 'archived']],
  ['reserved', ['sold', 'available']],
  ['in_workshop', ['available']],
  ['sold', ['archived']],
  ['archived', ['available']],
]);

/** A qué estados puede pasar un vehículo que hoy está en `estado`. */
export function transicionesDesde(estado: string): readonly string[] {
  return TRANSICIONES.get(estado) ?? [];
}

/**
 * Los seis estados en castellano — fuente unica.
 *
 * Estaban escritos dos veces: en la tabla y en los botones de cambio de estado.
 * Dos listas de lo mismo divergen, y el sintoma es una interfaz que llama
 * "Reservado" a una fila y "reserved" al boton de al lado.
 *
 * `Map` y no un objeto: leer `objeto[variable]` es acceso indexado y el linter
 * de seguridad lo marca —con razon en el caso general, aunque acá la clave
 * salga de nuestra propia tabla—. Un `Map` dice lo mismo sin la ambiguedad.
 */
export const NOMBRE_DE_ESTADO: ReadonlyMap<string, string> = new Map([
  ['in_preparation', 'En preparación'],
  ['available', 'Disponible'],
  ['reserved', 'Reservado'],
  ['sold', 'Vendido'],
  ['in_workshop', 'En taller'],
  ['archived', 'Archivado'],
]);

/** El nombre del estado, o el código crudo si es uno que no conocemos.
 *
 *  Devolver el código en vez de un guión es deliberado: un estado nuevo se ve
 *  feo pero se ve. Esconderlo lo dejaría invisible hasta que alguien pregunte
 *  por qué una fila no hace nada. */
export function nombreDeEstado(estado: string): string {
  return NOMBRE_DE_ESTADO.get(estado) ?? estado;
}

// ── La ficha ─────────────────────────────────────────────────────────────────

/**
 * El texto en castellano de un valor de catalogo cerrado.
 *
 * ⚠️ LOS CATALOGOS NO SE COPIAN ACA. `COMBUSTIBLES`, `TRANSMISIONES` y
 * `CARROCERIAS` ya viven en `lib/vehiculo-nuevo.ts`, espejados de los `StrEnum`
 * de `stock/schemas.py` y vigilados por `test_alta_espejada.py`. La ficha usa
 * ESOS mismos arreglos: una segunda tabla de traducciones acá seria una segunda
 * copia del mismo dominio, con un solo guardian mirando la primera — y el dia
 * que el backend agregue un combustible, una de las dos se enteraria.
 *
 * Que vivan en un modulo llamado `vehiculo-nuevo` es incomodo y es a proposito:
 * moverlos exigiria mover con ellos el guardian, que ademas cubre `ANIO_MINIMO`,
 * los largos maximos y los formatos de dominio — todos si especificos del alta.
 * Un import raro es visible; un guardian a medias no.
 *
 * Devuelve el codigo crudo si el valor no esta en el catalogo, por la misma
 * razon que `nombreDeEstado`: un valor nuevo se ve feo pero se ve.
 */
export function textoDeCatalogo(catalogo: readonly Opcion[], valor: string): string {
  return catalogo.find((opcion) => opcion.valor === valor)?.texto ?? valor;
}

/**
 * Una fecha ISO del backend, en formato argentino.
 *
 * `null` da guion y no cadena vacia: una celda vacia se lee como un error de
 * renderizado, y un guion dice "no hay dato" sin ambiguedad.
 *
 * ⚠️ SOLO LA FECHA, SIN LA HORA. `acquired_at`, `sold_at` y `created_at` son
 * `datetime` en el backend, pero la hora de una compra o una venta no le sirve a
 * nadie en la ficha y arrastra el problema de la zona horaria: el backend
 * serializa en UTC y mostrarla cruda diria "23:30 del dia anterior" para una
 * operacion de la tarde. Al recortar a la fecha se usa la zona de la agencia.
 */
export function formatearFecha(iso: string | null): string {
  if (iso === null) return '—';

  const fecha = new Date(iso);
  // Una fecha invalida da `NaN` y `toLocaleDateString` devolveria "Invalid Date"
  // en la pantalla. Se prefiere mostrar el crudo: al menos dice que llego algo.
  if (Number.isNaN(fecha.getTime())) return iso;

  return fecha.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'America/Argentina/Buenos_Aires',
  });
}

/**
 * Si un error al pedir un vehiculo significa "aca no hay nada".
 *
 * SON DOS ESTADOS HTTP Y NO UNO, y el segundo es el que se escapa:
 *
 *   404 — el id es valido y no hay fila. Puede ser un id inventado, un vehiculo
 *         dado de baja, o uno de OTRA agencia: la politica RLS hace que para
 *         esta sesion no exista. Las tres son lo mismo desde acá, y es a
 *         proposito — un 403 en la tercera confirmaria que el id es real.
 *
 *   422 — el id ni siquiera es un UUID. El endpoint lo declara `uuid.UUID`, asi
 *         que FastAPI lo rechaza ANTES de tocar la base. `/stock/cualquier-cosa`
 *         caia en el cartel de "el servicio no respondio", que es falso dos
 *         veces: el servicio respondio, y respondio bien. Es el unico parametro
 *         del endpoint, asi que un 422 acá no puede ser otra cosa.
 *
 * Vive en `lib/` y no en la pagina para poder probarse: la ficha importa
 * `@/auth` y eso no se monta en jsdom.
 */
export function noHayTalVehiculo(error: unknown): boolean {
  return error instanceof ErrorDeApi && (error.estado === 404 || error.estado === 422);
}
