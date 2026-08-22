/**
 * Las dos decisiones de la ficha que se pueden probar solas.
 *
 * La página en sí no se monta acá: importa `@/auth`, que arrastra NextAuth y con
 * él `next/server`, y eso no se levanta en jsdom. Es el mismo motivo por el que
 * `lib/stock.ts` existe — lo que se pueda probar solo, va donde se pueda probar
 * solo—, así que lo que se prueba es lo que se sacó de la página.
 *
 * `ESC-003` relaja el TDD estricto en el frontend: se prueban las costuras, no
 * cada componente. Estas dos SON costuras. `textoDeCatalogo` es el punto donde
 * la ficha se apoya en el catálogo espejado del backend, y `formatearFecha` es
 * el punto donde una fecha en UTC se convierte en un día del calendario — que es
 * donde se corre un día entero si nadie mira.
 */
import { describe, expect, it } from 'vitest';

import { ErrorDeApi } from '@/lib/api';
import { formatearFecha, noHayTalVehiculo, textoDeCatalogo } from '@/lib/stock';
import { CARROCERIAS, COMBUSTIBLES, TRANSMISIONES } from '@/lib/vehiculo-nuevo';

describe('textoDeCatalogo', () => {
  it('traduce los valores de los tres catálogos', () => {
    expect(textoDeCatalogo(COMBUSTIBLES, 'gasoline')).toBe('Nafta');
    expect(textoDeCatalogo(TRANSMISIONES, 'automatic')).toBe('Automática');
    expect(textoDeCatalogo(CARROCERIAS, 'wagon')).toBe('Familiar');
  });

  it('devuelve el código crudo si el backend manda uno que no conocemos', () => {
    // La dirección segura de la deriva: el backend agrega `hydrogen` y la ficha
    // muestra "hydrogen". Feo, pero visible. Devolver un guión lo escondería
    // hasta que alguien preguntara por qué ese auto no tiene combustible.
    expect(textoDeCatalogo(COMBUSTIBLES, 'hydrogen')).toBe('hydrogen');
  });

  it('no confunde un catálogo con otro', () => {
    // `other` está en CARROCERIAS y no en COMBUSTIBLES. Si la búsqueda mirara
    // los tres arreglos juntos, esto devolvería "Otra" para un combustible.
    expect(textoDeCatalogo(CARROCERIAS, 'other')).toBe('Otra');
    expect(textoDeCatalogo(COMBUSTIBLES, 'other')).toBe('other');
  });
});

describe('formatearFecha', () => {
  it('muestra un guión cuando no hay fecha', () => {
    expect(formatearFecha(null)).toBe('—');
  });

  it('formatea en día/mes/año', () => {
    expect(formatearFecha('2026-08-15T13:45:00Z')).toBe('15/08/2026');
  });

  it('usa la zona horaria de la agencia y no la del servidor — el caso que corre un día', () => {
    // 02:30 UTC del 1 de agosto son las 23:30 del 31 de julio en Buenos Aires.
    // Sin `timeZone` esto daría un día distinto según dónde corra el proceso de
    // Next: en el VPS, la fecha de una compra de la noche aparecería al día
    // siguiente. Es el error que no se ve hasta que un contador lo reclama.
    expect(formatearFecha('2026-08-01T02:30:00Z')).toBe('31/07/2026');
  });

  it('devuelve el crudo si la fecha no se puede interpretar', () => {
    // `new Date('mañana')` da `Invalid Date`, y `toLocaleDateString` lo
    // renderizaría literalmente como "Invalid Date" en la pantalla. Mostrar lo
    // que llegó al menos dice qué llegó.
    expect(formatearFecha('mañana')).toBe('mañana');
  });
});

describe('noHayTalVehiculo', () => {
  it('dice que sí ante un 404 — el id es válido y no hay fila', () => {
    expect(noHayTalVehiculo(new ErrorDeApi(404, '/api/v1/vehicles/x'))).toBe(true);
  });

  it('dice que sí ante un 422 — el id ni siquiera es un UUID', () => {
    // El caso que se escapaba. El endpoint declara el parámetro `uuid.UUID`, así
    // que FastAPI rechaza `/stock/cualquier-cosa` con 422 antes de tocar la base,
    // y la ficha mostraba "el servicio no respondió" — falso dos veces.
    expect(noHayTalVehiculo(new ErrorDeApi(422, '/api/v1/vehicles/cualquier-cosa'))).toBe(true);
  });

  it('dice que NO ante un 403 — eso es un problema de permisos, no un vacío', () => {
    // Un 403 tiene que llegar al cartel de error, no a la pantalla de "no
    // encontrado": el vehículo existe y la respuesta correcta es explicarlo.
    expect(noHayTalVehiculo(new ErrorDeApi(403, '/api/v1/vehicles/x'))).toBe(false);
  });

  it('dice que NO ante un 500 ni ante un error de red', () => {
    expect(noHayTalVehiculo(new ErrorDeApi(500, '/api/v1/vehicles/x'))).toBe(false);
    // Un `fetch` que ni siquiera llegó no es un `ErrorDeApi`. Si esto devolviera
    // `true`, el backend caído se vería como "ese vehículo no existe" y nadie
    // sabría que hay un servicio abajo.
    expect(noHayTalVehiculo(new TypeError('fetch failed'))).toBe(false);
  });
});
