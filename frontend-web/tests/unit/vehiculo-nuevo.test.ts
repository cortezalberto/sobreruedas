/**
 * El alta de un vehículo: qué se valida acá y qué se le deja al backend.
 *
 * LA VALIDACIÓN DEL CLIENTE NO ES LA AUTORIDAD — el backend rechaza igual lo
 * que esté mal. Existe por un motivo concreto y verificado contra el backend
 * CORRIENDO el 21-ago-2026:
 *
 *   POST /vehicles con "XX-9" de dominio  ->  422, field: "body"
 *   POST /vehicles sin dominio ni chasis  ->  422, field: "body"
 *
 * Las dos reglas viven en un `model_validator(mode="after")` de Pydantic, así
 * que el error se atribuye al CUERPO ENTERO y no al campo. Un formulario que
 * solo repita lo que el backend dice no puede pintar de rojo el campo que está
 * mal, porque el backend no se lo dice. Por eso se validan acá también.
 *
 * Lo que NO se valida acá, a propósito:
 *   - el dominio duplicado (`RN-ST-01`): exige mirar el stock de la agencia
 *   - la cuota del plan: la sabe el backend y responde 402
 *   - quién puede dar de alta: es la matriz de permisos y NO se copia al cliente
 */
import { describe, expect, it } from 'vitest';

import {
  aCuerpo,
  BORRADOR_VACIO,
  CARROCERIAS,
  COMBUSTIBLES,
  mensajeDeAlta,
  normalizarChasis,
  normalizarDominio,
  TRANSMISIONES,
  validar,
  type BorradorDeVehiculo,
} from '@/lib/vehiculo-nuevo';

/** Un borrador que pasa todas las reglas. Cada test rompe UNA cosa. */
function borrador(extra: Partial<BorradorDeVehiculo> = {}): BorradorDeVehiculo {
  return {
    ...BORRADOR_VACIO,
    branch_id: '22222222-2222-2222-2222-222222222222',
    brand_id: '00000000-0000-4000-8000-0000000000b1',
    model_id: '00000000-0000-4000-8000-0000000000m1',
    domain_plate: 'AB123CD',
    year: '2020',
    mileage_km: '45000',
    color: 'Gris',
    fuel_type: 'gasoline',
    transmission: 'manual',
    body_type: 'sedan',
    price_ars: '18500000',
    ...extra,
  };
}

describe('normalizar el dominio', () => {
  it('acepta el formato viejo y el Mercosur, en minúsculas y con separadores', () => {
    // Los cuatro son el MISMO dominio escrito distinto. Si no se normalizara,
    // el chequeo de duplicados del backend los tomaría por vehículos distintos.
    expect(normalizarDominio('abc123')).toBe('ABC123');
    expect(normalizarDominio('ABC 123')).toBe('ABC123');
    expect(normalizarDominio('ab123cd')).toBe('AB123CD');
    expect(normalizarDominio('AB-123-CD')).toBe('AB123CD');
  });

  it('devuelve null cuando no es un formato argentino', () => {
    expect(normalizarDominio('XX9')).toBeNull();
    expect(normalizarDominio('ABCD123')).toBeNull();
    expect(normalizarDominio('123ABC')).toBeNull();
  });
});

describe('normalizar el chasis', () => {
  it('exige 17 caracteres y rechaza I, O y Q', () => {
    expect(normalizarChasis('8ajfr22g30k123456')).toBe('8AJFR22G30K123456');
    // Se excluyen para no confundirlas con 1 y 0 — es el estándar del VIN, y el
    // backend usa exactamente la misma clase de caracteres.
    expect(normalizarChasis('8AJFR22G30I123456')).toBeNull();
    expect(normalizarChasis('8AJFR22G30K12345')).toBeNull();
  });
});

describe('validar el borrador', () => {
  it('no encuentra nada que objetar en uno completo', () => {
    expect(validar(borrador())).toEqual({});
  });

  it('exige sucursal, marca y modelo', () => {
    const errores = validar(borrador({ branch_id: '', brand_id: '', model_id: '' }));

    expect(errores.branch_id).toBeDefined();
    expect(errores.brand_id).toBeDefined();
    expect(errores.model_id).toBeDefined();
  });

  it('exige al menos dominio o chasis, y lo dice en el dominio', () => {
    // `ADR-031`: un 0 km sin patentar no tiene dominio, así que el campo es
    // opcional — pero un vehículo sin NINGUNA forma de identificarse no se
    // distingue de otro. El error se cuelga del dominio porque es el campo que
    // el usuario va a completar en el 95 % de los casos.
    const errores = validar(borrador({ domain_plate: '', chassis_number: '' }));

    expect(errores.domain_plate).toContain('chasis');
  });

  it('acepta el chasis solo, sin dominio', () => {
    const errores = validar(borrador({ domain_plate: '', chassis_number: '8AJFR22G30K123456' }));

    expect(errores).toEqual({});
  });

  it('marca el dominio mal formado en SU campo', () => {
    // Esta es la razón de ser de este módulo: el backend manda este error con
    // `field: "body"` y el formulario no sabría a quién culpar.
    const errores = validar(borrador({ domain_plate: 'XX9' }));

    expect(errores.domain_plate).toBeDefined();
    expect(errores.chassis_number).toBeUndefined();
  });

  it('marca el chasis mal formado en SU campo', () => {
    const errores = validar(borrador({ chassis_number: 'CORTO' }));

    expect(errores.chassis_number).toBeDefined();
  });

  it('rechaza un año anterior a 1950 y posterior al que viene', () => {
    const proximo = new Date().getFullYear() + 1;

    expect(validar(borrador({ year: '1949' })).year).toBeDefined();
    expect(validar(borrador({ year: String(proximo + 1) })).year).toBeDefined();
    // `RN-ST-03`: el modelo del año siguiente se carga antes de que termine el
    // año en curso. Cortar en el año actual dejaría afuera un caso normal.
    expect(validar(borrador({ year: String(proximo) })).year).toBeUndefined();
  });

  it('rechaza un año que no es un número', () => {
    expect(validar(borrador({ year: 'dos mil' })).year).toBeDefined();
    expect(validar(borrador({ year: '' })).year).toBeDefined();
  });

  it('rechaza kilómetros negativos y acepta cero', () => {
    expect(validar(borrador({ mileage_km: '-1' })).mileage_km).toBeDefined();
    // Un 0 km tiene 0 km. Es el caso más común de una concesionaria oficial.
    expect(validar(borrador({ mileage_km: '0' })).mileage_km).toBeUndefined();
  });

  it('exige un precio mayor que cero', () => {
    expect(validar(borrador({ price_ars: '0' })).price_ars).toBeDefined();
    expect(validar(borrador({ price_ars: '-5' })).price_ars).toBeDefined();
    expect(validar(borrador({ price_ars: '' })).price_ars).toBeDefined();
  });

  it('exige color, combustible, transmisión y carrocería', () => {
    const errores = validar(
      borrador({ color: '', fuel_type: '', transmission: '', body_type: '' }),
    );

    expect(errores.color).toBeDefined();
    expect(errores.fuel_type).toBeDefined();
    expect(errores.transmission).toBeDefined();
    expect(errores.body_type).toBeDefined();
  });

  it('respeta los largos máximos del schema', () => {
    // `color` es `max_length=60` y `engine_number` `max_length=30` en
    // `stock/schemas.py`. Sin esto el backend responde 422 con
    // `field: "body.color"`, que `mensajeDeAlta` no traduce a propósito — el
    // usuario vería "El backend rechazó el alta (422)" y ninguna pista de qué
    // campo achicar.
    expect(validar(borrador({ color: 'a'.repeat(61) })).color).toBeDefined();
    expect(validar(borrador({ color: 'a'.repeat(60) })).color).toBeUndefined();

    expect(validar(borrador({ engine_number: 'a'.repeat(31) })).engine_number).toBeDefined();
    expect(validar(borrador({ engine_number: 'a'.repeat(30) })).engine_number).toBeUndefined();
  });

  it('acepta el costo vacío y rechaza uno negativo', () => {
    // Opcional: `RN-ST-12` lo esconde a un vendedor, y una agencia puede cargar
    // el auto antes de saber en cuánto lo tomó.
    expect(validar(borrador({ acquisition_cost_ars: '' })).acquisition_cost_ars).toBeUndefined();
    expect(validar(borrador({ acquisition_cost_ars: '-1' })).acquisition_cost_ars).toBeDefined();
  });
});

describe('armar el cuerpo del POST', () => {
  it('manda los obligatorios con el tipo que el backend espera', () => {
    const cuerpo = aCuerpo(borrador());

    // Números como números y plata como string: `price_ars` es `Decimal` del
    // lado de Pydantic y un `number` de JavaScript perdería centavos en un
    // precio de ocho cifras.
    expect(cuerpo).toMatchObject({
      branch_id: '22222222-2222-2222-2222-222222222222',
      year: 2020,
      mileage_km: 45000,
      color: 'Gris',
      fuel_type: 'gasoline',
      price_ars: '18500000',
    });
    expect(typeof cuerpo.year).toBe('number');
    expect(typeof cuerpo.price_ars).toBe('string');
  });

  it('normaliza el dominio y el chasis antes de mandarlos', () => {
    const cuerpo = aCuerpo(borrador({ domain_plate: 'ab-123-cd' }));

    expect(cuerpo.domain_plate).toBe('AB123CD');
  });

  it('OMITE los opcionales vacíos en vez de mandarlos en blanco', () => {
    // No es cosmético: el schema del backend es `extra="forbid"` y los campos
    // son `str | None`. Un `""` en `chassis_number` pasaría el tipo y quedaría
    // guardado como cadena vacía, que después no es ni un chasis ni un `null`.
    const cuerpo = aCuerpo(borrador({ chassis_number: '', description: '', price_usd: '' }));

    expect('chassis_number' in cuerpo).toBe(false);
    expect('description' in cuerpo).toBe(false);
    expect('price_usd' in cuerpo).toBe(false);
  });

  it('NUNCA manda tenant_id ni status', () => {
    // Regla dura 1: el tenant sale del token. Y `status` lo fija `RN-ST-04`.
    // El backend rechaza los dos con `extra_forbidden` — verificado en vivo—,
    // así que mandarlos sería un 422 garantizado.
    const cuerpo: Record<string, unknown> = { ...aCuerpo(borrador()) };

    expect('tenant_id' in cuerpo).toBe(false);
    expect('status' in cuerpo).toBe(false);
    expect('assigned_user_id' in cuerpo).toBe(false);
  });
});

describe('los catálogos de opciones', () => {
  it('cubren exactamente los valores que el backend admite', () => {
    // Copiados del enum de `schemas.py`. Son conocimiento de DOMINIO —qué
    // combustibles existen— y no la matriz de permisos, así que copiarlos es
    // legítimo por la misma división que fija `ADR-034` para las transiciones.
    expect(COMBUSTIBLES.map((o) => o.valor)).toEqual([
      'gasoline',
      'diesel',
      'hybrid',
      'electric',
      'gnc',
      'flex',
    ]);
    expect(TRANSMISIONES.map((o) => o.valor)).toEqual(['manual', 'automatic', 'cvt', 'dsg']);
    expect(CARROCERIAS.map((o) => o.valor)).toEqual([
      'sedan',
      'hatchback',
      'suv',
      'pickup',
      'van',
      'coupe',
      'wagon',
      'other',
    ]);
  });

  it('todas las opciones tienen texto en castellano', () => {
    for (const opcion of [...COMBUSTIBLES, ...TRANSMISIONES, ...CARROCERIAS]) {
      expect(opcion.texto.length).toBeGreaterThan(0);
      expect(opcion.texto).not.toBe(opcion.valor);
    }
  });
});

describe('traducir el rechazo del backend', () => {
  it('explica los tres rechazos que mandan por caminos distintos', () => {
    // No se colapsan en "no se pudo": cada uno se arregla haciendo algo
    // distinto, y decir "no se pudo" deja a las tres personas sin saber qué.
    //   403 -> pedirle el alta a un gerente
    //   402 -> subir de plan (ningún permiso lo arregla)
    //   422 -> corregir el dominio repetido
    expect(mensajeDeAlta('insufficient_permission', 403)).toMatch(/rol/i);
    expect(mensajeDeAlta('plan_quota_exceeded', 402)).toMatch(/plan/i);
    expect(mensajeDeAlta('domain_error', 422)).toMatch(/dominio/i);
  });

  it('manda a iniciar sesión cuando el token venció', () => {
    expect(mensajeDeAlta('not_authenticated', 401)).toMatch(/sesión/i);
  });

  it('entiende el código propio del duplicado, sin importar el estado', () => {
    // `vehicle_duplicate` es un código ESPECIFICO: no necesita el 422 para
    // desambiguarse, porque nombra la regla incumplida (`RN-ST-01`) en vez de
    // decir "alguna regla de negocio". Se traduce por el código a secas.
    expect(mensajeDeAlta('vehicle_duplicate', 422)).toMatch(/dominio/i);
  });

  it('sigue entendiendo el código viejo mientras dure la ventana de despliegue', () => {
    // ⚠️ ESTE TEST NO SOBRA, Y NO SE BORRA HASTA QUE EL BACKEND NUEVO ESTE
    // DESPLEGADO. El frontend y el backend no salen en el mismo instante: entre
    // un despliegue y el otro hay una ventana en la que este frontend habla con
    // el backend viejo, que todavia manda `domain_error`. Si solo entendiera el
    // codigo nuevo, en esa ventana el duplicado —el rechazo MAS FRECUENTE del
    // alta— degradaria a "El backend rechazó el alta (422)".
    //
    // Es el mismo criterio de expand → migrar → contract que la regla dura 13
    // le aplica a las migraciones, aplicado a un contrato de API: primero se
    // aceptan los dos, despues cambia el emisor, y recien al final se saca el
    // viejo.
    expect(mensajeDeAlta('domain_error', 422)).toMatch(/dominio/i);
  });

  it('devuelve null ante un código que no conocemos', () => {
    // Devolver null y no un mensaje inventado: quien llama arma el fallback con
    // el estado HTTP, que al menos es cierto. Un mensaje traducido de más
    // mentiría con cara de estar bien.
    expect(mensajeDeAlta('un_codigo_nuevo', 500)).toBeNull();
    expect(mensajeDeAlta('', 500)).toBeNull();
  });

  it('NO traduce validation_error a un texto genérico', () => {
    // `validation_error` significa que un campo puntual está mal, y el
    // formulario ya lo valida antes de mandar. Si llega igual es que la
    // validación del cliente y la del backend divergieron — un mensaje amable
    // escondería justamente el síntoma que hace falta ver.
    expect(mensajeDeAlta('validation_error', 422)).toBeNull();
  });
});
