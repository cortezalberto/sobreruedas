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
  ];
}
