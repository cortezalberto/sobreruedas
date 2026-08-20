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

import { columnasPara, elBackendMandaElCosto, TRANSICIONES, transicionesDesde } from '@/lib/stock';
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

describe('las transiciones que la UI ofrece', () => {
  it('reflejan `RN-ST-05` y no la matriz de permisos', () => {
    // Desde `available` la máquina admite tres. Que un `salesperson` solo pueda
    // una de ellas NO se decide acá — lo decide el backend, y por eso los tres
    // botones se ofrecen igual. Ver el comentario de `TRANSICIONES`.
    expect([...transicionesDesde('available')].sort()).toEqual([
      'archived',
      'in_workshop',
      'reserved',
    ]);
  });

  it('no ofrecen el salto que ningún rol puede hacer', () => {
    // `in_preparation` -> `sold` no existe para nadie, ni para el gerente. Es
    // dominio, no permisos, y por eso sí corresponde esconderlo.
    expect(transicionesDesde('in_preparation')).not.toContain('sold');
    expect(transicionesDesde('in_preparation')).toEqual(['available']);
  });

  it('desde `reserved` se puede vender o soltar la reserva', () => {
    expect([...transicionesDesde('reserved')].sort()).toEqual(['available', 'sold']);
  });

  it('un estado desconocido no ofrece nada, en vez de romper', () => {
    // El backend podría agregar un estado antes que esta copia. Devolver una
    // lista vacía deja la fila sin botones —visible— en lugar de reventar el
    // render de la tabla entera.
    expect(transicionesDesde('paused')).toEqual([]);
  });

  it('los seis estados de `ADR-031` están cubiertos', () => {
    // `Pausado` NO está, y no es un olvido: es estado de la publicación, no del
    // vehículo. Si alguien lo agrega acá, este test lo delata.
    expect([...TRANSICIONES.keys()].sort()).toEqual([
      'archived',
      'available',
      'in_preparation',
      'in_workshop',
      'reserved',
      'sold',
    ]);
  });

  it('todo destino ofrecido es a su vez un estado conocido', () => {
    // Un destino que no sea estado válido produciría un botón que el backend
    // rechaza siempre con 422 — un callejón sin salida en la interfaz.
    const estados = new Set(TRANSICIONES.keys());
    for (const [, destinos] of TRANSICIONES) {
      for (const destino of destinos) {
        expect(estados.has(destino)).toBe(true);
      }
    }
  });
});
