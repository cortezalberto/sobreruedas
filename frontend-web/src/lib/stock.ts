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
import type { Vehiculo } from '@/lib/api';

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
