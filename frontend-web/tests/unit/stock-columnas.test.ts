/**
 * La columna de costo aparece o no según lo que el backend mande — `RN-ST-12`.
 *
 * Es la única decisión de la pantalla de stock que puede estar mal de una forma
 * que se ve como si estuviera bien: si se esconde de más, el gerente no ve un
 * dato que sí le corresponde; si se muestra de más, la tabla saca una columna
 * vacía donde el backend nunca mandó nada.
 *
 * Los tres casos son distintos y hay que separarlos, porque `null` y ausente
 * NO significan lo mismo:
 *
 *   ausente  -> este rol no puede verlo
 *   null     -> puede verlo, y este vehículo no lo tiene cargado
 *   "123.00" -> puede verlo y está cargado
 */
import { describe, expect, it } from 'vitest';

import { columnasPara, elBackendMandaElCosto } from '@/lib/stock';
import type { Vehiculo } from '@/lib/api';

/** Un vehículo mínimo. Los campos que no importan acá se rellenan igual porque
 *  el tipo los exige, y exigirlos es lo que evita que el test mienta. */
function vehiculo(extra: Partial<Vehiculo> = {}): Vehiculo {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    domain_plate: 'AB123CD',
    chassis_number: null,
    brand_id: '00000000-0000-4000-8000-0000000000b1',
    model_id: '00000000-0000-4000-8000-0000000000m1',
    year: 2021,
    mileage_km: 30000,
    color: 'Blanco',
    status: 'available',
    price_ars: '15000000.00',
    ...extra,
  };
}

describe('la columna de costo', () => {
  it('no aparece cuando el backend NO mandó la clave', () => {
    // Lo que recibe un `salesperson`: 23 campos, sin `acquisition_cost_ars`.
    const stock = [vehiculo(), vehiculo()];

    expect(elBackendMandaElCosto(stock)).toBe(false);
    expect(columnasPara(stock)).not.toContain('Costo');
  });

  it('aparece cuando el backend mandó un valor', () => {
    const stock = [vehiculo({ acquisition_cost_ars: '11000000.00' })];

    expect(elBackendMandaElCosto(stock)).toBe(true);
    expect(columnasPara(stock)).toContain('Costo');
  });

  it('aparece aunque el valor sea `null` — el caso que casi se escapa', () => {
    // Un gerente mirando un vehículo sin costo cargado. La clave VIENE, en
    // `null`. Preguntar `!== undefined` escondería la columna a quien sí puede
    // verla, que es el estado normal de una agencia que recién carga sus autos.
    const stock = [vehiculo({ acquisition_cost_ars: null })];

    expect(elBackendMandaElCosto(stock)).toBe(true);
    expect(columnasPara(stock)).toContain('Costo');
  });

  it('alcanza con que UN vehículo la traiga', () => {
    // El backend recorta por rol, no por fila: o los manda todos o ninguno. Se
    // afirma igual porque la tabla es una sola y una decisión por fila daría
    // una grilla con agujeros.
    const stock = [vehiculo(), vehiculo({ acquisition_cost_ars: '900.00' })];

    expect(columnasPara(stock)).toContain('Costo');
  });

  it('con el stock vacío no la agrega', () => {
    expect(elBackendMandaElCosto([])).toBe(false);
    expect(columnasPara([])).not.toContain('Costo');
  });

  it('las demás columnas no dependen del rol', () => {
    const sinCosto = columnasPara([vehiculo()]);
    const conCosto = columnasPara([vehiculo({ acquisition_cost_ars: '1.00' })]);

    // Lo único que cambia es la de costo. Si mañana alguien recorta otra
    // columna por rol desde el cliente, esto lo delata.
    expect(conCosto.filter((c) => c !== 'Costo')).toEqual(sinCosto);
  });
});
