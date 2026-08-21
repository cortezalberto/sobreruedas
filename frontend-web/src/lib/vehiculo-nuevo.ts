/**
 * El alta de un vehículo, SIN dependencias de framework.
 *
 * Vive en `lib/` por el mismo motivo que `lib/stock.ts`: lo que se pueda probar
 * solo, va donde se pueda probar solo. El formulario importa de acá, no al revés.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * POR QUÉ HAY VALIDACIÓN ACÁ SI EL BACKEND YA VALIDA
 * ─────────────────────────────────────────────────────────────────────────
 * No es desconfianza ni redundancia defensiva. Es un límite REAL del contrato,
 * medido contra el backend corriendo el 21-ago-2026:
 *
 *     POST /vehicles  dominio "XX-9"        -> 422  field: "body"
 *     POST /vehicles  sin dominio ni chasis -> 422  field: "body"
 *
 * Las dos reglas están en un `model_validator(mode="after")` de Pydantic, que
 * corre sobre el modelo YA armado y por eso atribuye el error al cuerpo entero.
 * El backend, literalmente, no sabe decir qué campo pintar de rojo. Un
 * formulario que solo reprodujera su respuesta mostraría "hay algo mal" sin
 * decir dónde, que en un formulario de catorce campos es lo mismo que nada.
 *
 * LO QUE NO SE VALIDA ACÁ, Y NO ES UN OLVIDO:
 *   - dominio duplicado (`RN-ST-01`): exige mirar el stock de la agencia
 *   - cuota del plan: la sabe el backend y responde 402
 *   - QUIÉN puede dar de alta: es la matriz de permisos y **no se copia**.
 *     Misma división que `ADR-034` fija para las transiciones: el dominio se
 *     copia, los permisos no. Una copia de la matriz en el cliente es una
 *     segunda fuente de verdad, y encima editable desde el navegador.
 */

/** Una opción de un desplegable. Coincide con lo que `Seleccion` espera. */
export interface Opcion {
  valor: string;
  texto: string;
}

/**
 * Los catálogos cerrados, copiados de los `StrEnum` de `stock/schemas.py`.
 *
 * Se copian por la misma razón que `TRANSICIONES`: qué combustibles existe es
 * conocimiento de dominio, no una decisión de permisos. El riesgo de la copia
 * es la deriva —el backend agrega un valor y acá no aparece—, y la dirección
 * de esa falla es la segura: falta una opción, no se ofrece una inválida.
 */
export const COMBUSTIBLES: readonly Opcion[] = [
  { valor: 'gasoline', texto: 'Nafta' },
  { valor: 'diesel', texto: 'Diésel' },
  { valor: 'hybrid', texto: 'Híbrido' },
  { valor: 'electric', texto: 'Eléctrico' },
  { valor: 'gnc', texto: 'GNC' },
  { valor: 'flex', texto: 'Flex' },
];

export const TRANSMISIONES: readonly Opcion[] = [
  { valor: 'manual', texto: 'Manual' },
  { valor: 'automatic', texto: 'Automática' },
  { valor: 'cvt', texto: 'CVT' },
  { valor: 'dsg', texto: 'DSG' },
];

export const CARROCERIAS: readonly Opcion[] = [
  { valor: 'sedan', texto: 'Sedán' },
  { valor: 'hatchback', texto: 'Hatchback' },
  { valor: 'suv', texto: 'SUV' },
  { valor: 'pickup', texto: 'Pickup' },
  { valor: 'van', texto: 'Van' },
  { valor: 'coupe', texto: 'Coupé' },
  { valor: 'wagon', texto: 'Familiar' },
  { valor: 'other', texto: 'Otra' },
];

/** `RN-ST-03` / `ANIO_MINIMO` de `schemas.py`. */
export const ANIO_MINIMO = 1950;

/**
 * Los largos máximos, copiados de `VehiculoCrear` en `stock/schemas.py`.
 *
 * Se espejan por el mismo motivo que las reglas de `ADR-031`: pasarse devuelve
 * un 422 que `mensajeDeAlta` no traduce a propósito, así que el usuario vería
 * "El backend rechazó el alta (422)" sin ninguna pista de qué campo achicar.
 */
export const LARGO_MAXIMO_COLOR = 60;
export const LARGO_MAXIMO_MOTOR = 30;

/**
 * El borrador es TODO strings, porque eso es lo que da un `<input>`.
 *
 * La conversión a número o a decimal pasa una sola vez, en `aCuerpo`. Tener el
 * estado del formulario ya tipado obligaría a decidir qué es `year` mientras el
 * usuario tipeó "20" camino a "2020", y la respuesta honesta es "todavía nada".
 */
export interface BorradorDeVehiculo {
  branch_id: string;
  brand_id: string;
  model_id: string;
  domain_plate: string;
  chassis_number: string;
  engine_number: string;
  year: string;
  mileage_km: string;
  color: string;
  fuel_type: string;
  transmission: string;
  body_type: string;
  price_ars: string;
  price_usd: string;
  acquisition_cost_ars: string;
  description: string;
}

export const BORRADOR_VACIO: BorradorDeVehiculo = {
  branch_id: '',
  brand_id: '',
  model_id: '',
  domain_plate: '',
  chassis_number: '',
  engine_number: '',
  year: '',
  mileage_km: '',
  color: '',
  fuel_type: '',
  transmission: '',
  body_type: '',
  price_ars: '',
  price_usd: '',
  acquisition_cost_ars: '',
  description: '',
};

// Formato viejo `AAA999` y Mercosur `AA999AA`. Los mismos dos que
// `normalizar_dominio` del backend, y por el mismo motivo: el mismo dominio
// escrito de dos formas no puede producir dos vehículos.
const DOMINIO_VIEJO = /^[A-Z]{3}[0-9]{3}$/;
const DOMINIO_MERCOSUR = /^[A-Z]{2}[0-9]{3}[A-Z]{2}$/;

// VIN: 17 caracteres sin I, O ni Q — se excluyen para no confundirlas con 1 y 0.
const CHASIS = /^[A-HJ-NPR-Z0-9]{17}$/;

const SEPARADORES = /[\s-]/g;

/** El dominio en mayúsculas y sin separadores, o `null` si no es formato AR. */
export function normalizarDominio(valor: string): string | null {
  const limpio = valor.replace(SEPARADORES, '').toUpperCase();
  return DOMINIO_VIEJO.test(limpio) || DOMINIO_MERCOSUR.test(limpio) ? limpio : null;
}

/** El chasis normalizado, o `null` si no es un VIN de 17 sin I, O ni Q. */
export function normalizarChasis(valor: string): string | null {
  const limpio = valor.replace(SEPARADORES, '').toUpperCase();
  return CHASIS.test(limpio) ? limpio : null;
}

/** Los errores del borrador, por campo. Vacío significa que se puede mandar. */
export type ErroresDelBorrador = Partial<Record<keyof BorradorDeVehiculo, string>>;

/**
 * Un entero a partir de lo que el usuario escribió, o `null`.
 *
 * `Number('')` es `0` y `Number('  ')` también, así que el vacío se descarta
 * antes. Sin eso, un campo en blanco pasaría como cero y "kilómetros vacío" se
 * guardaría como "0 km", que es un dato distinto y creíble.
 */
function entero(valor: string): number | null {
  const texto = valor.trim();
  if (texto === '' || !/^-?\d+$/.test(texto)) return null;
  return Number(texto);
}

const SOLO_DIGITOS = /^\d+$/;

/**
 * Un decimal a partir de lo que el usuario escribió, o `null`.
 *
 * Acepta la coma como separador porque es la que tiene el teclado de acá, y
 * porque `18.500.000,50` es como se escribe un precio en castellano. Se
 * convierte a punto antes de parsear.
 *
 * PARTIDO EN DOS EN VEZ DE UNA REGEX SOLA. La forma directa —`^-?\d+(\.\d+)?$`—
 * hace que `safe-regex` la marque como potencialmente exponencial. Es un falso
 * positivo (no hay ambigüedad entre las dos partes), pero dejar la advertencia
 * puesta con un comentario que diga "no pasa nada" es la forma en que un repo
 * se acostumbra a las advertencias. Partirla cuesta cuatro líneas y deja el
 * lint sin nada que decir.
 */
function decimal(valor: string): number | null {
  const texto = valor.trim().replace(',', '.');
  if (texto === '') return null;

  const sinSigno = texto.startsWith('-') ? texto.slice(1) : texto;
  const partes = sinSigno.split('.');
  if (partes.length > 2 || !partes.every((parte) => SOLO_DIGITOS.test(parte))) return null;

  const numero = Number(texto);
  return Number.isFinite(numero) ? numero : null;
}

export function validar(borrador: BorradorDeVehiculo): ErroresDelBorrador {
  const errores: ErroresDelBorrador = {};

  if (borrador.branch_id === '') errores.branch_id = 'Elegí la sucursal donde está el vehículo.';
  if (borrador.brand_id === '') errores.brand_id = 'Elegí la marca.';
  if (borrador.model_id === '') errores.model_id = 'Elegí el modelo.';
  if (borrador.color.trim() === '') {
    errores.color = 'Poné el color.';
  } else if (borrador.color.trim().length > LARGO_MAXIMO_COLOR) {
    errores.color = `El color entra en ${LARGO_MAXIMO_COLOR} caracteres.`;
  }
  if (borrador.engine_number.trim().length > LARGO_MAXIMO_MOTOR) {
    errores.engine_number = `El número de motor entra en ${LARGO_MAXIMO_MOTOR} caracteres.`;
  }
  if (borrador.fuel_type === '') errores.fuel_type = 'Elegí el combustible.';
  if (borrador.transmission === '') errores.transmission = 'Elegí la transmisión.';
  if (borrador.body_type === '') errores.body_type = 'Elegí la carrocería.';

  // ── Identificación: `ADR-031` ──────────────────────────────────────────
  const tieneDominio = borrador.domain_plate.trim() !== '';
  const tieneChasis = borrador.chassis_number.trim() !== '';

  if (!tieneDominio && !tieneChasis) {
    // El mensaje va en el dominio y no en los dos campos: repetirlo en ambos
    // haría parecer que faltan dos cosas cuando alcanza con una.
    errores.domain_plate = 'Hace falta el dominio o el número de chasis.';
  }
  if (tieneDominio && normalizarDominio(borrador.domain_plate) === null) {
    errores.domain_plate = 'El dominio tiene que ser AAA999 o AA999AA.';
  }
  if (tieneChasis && normalizarChasis(borrador.chassis_number) === null) {
    errores.chassis_number = 'El chasis tiene 17 caracteres, sin I, O ni Q.';
  }

  // ── Año: `RN-ST-03` ────────────────────────────────────────────────────
  const anio = entero(borrador.year);
  // El máximo es el año QUE VIENE: las agencias cargan el modelo siguiente
  // antes de que termine el año en curso. Cortar en el actual dejaría afuera
  // un caso normal, no un error.
  const anioMaximo = new Date().getFullYear() + 1;
  if (anio === null) {
    errores.year = 'Poné el año en números.';
  } else if (anio < ANIO_MINIMO || anio > anioMaximo) {
    errores.year = `El año va entre ${ANIO_MINIMO} y ${anioMaximo}.`;
  }

  const kilometros = entero(borrador.mileage_km);
  if (kilometros === null) {
    errores.mileage_km = 'Poné los kilómetros en números.';
  } else if (kilometros < 0) {
    errores.mileage_km = 'Los kilómetros no pueden ser negativos.';
  }

  const precio = decimal(borrador.price_ars);
  if (precio === null) {
    errores.price_ars = 'Poné el precio de venta.';
  } else if (precio <= 0) {
    errores.price_ars = 'El precio tiene que ser mayor que cero.';
  }

  // ── Opcionales: vacío está bien, mal escrito no ────────────────────────
  // Escritos uno por uno y no en un bucle sobre una lista de nombres de campo:
  // el bucle obliga a indexar `borrador[campo]` con una clave variable, que es
  // exactamente el patron que marca `security/detect-object-injection`. Con dos
  // campos, desenrollarlo cuesta menos que explicar por que es seguro.
  const MONTO_INVALIDO = 'Tiene que ser un monto mayor que cero.';

  if (borrador.price_usd.trim() !== '') {
    const dolares = decimal(borrador.price_usd);
    if (dolares === null || dolares <= 0) errores.price_usd = MONTO_INVALIDO;
  }
  if (borrador.acquisition_cost_ars.trim() !== '') {
    const costo = decimal(borrador.acquisition_cost_ars);
    if (costo === null || costo <= 0) errores.acquisition_cost_ars = MONTO_INVALIDO;
  }

  return errores;
}

/** El cuerpo del `POST /api/v1/vehicles`, listo para `JSON.stringify`. */
export interface CuerpoDeAlta {
  branch_id: string;
  brand_id: string;
  model_id: string;
  year: number;
  mileage_km: number;
  color: string;
  fuel_type: string;
  transmission: string;
  body_type: string;
  price_ars: string;
  domain_plate?: string;
  chassis_number?: string;
  engine_number?: string;
  price_usd?: string;
  acquisition_cost_ars?: string;
  description?: string;
}

/**
 * El borrador convertido al contrato del backend.
 *
 * ⚠️ LOS MONTOS VIAJAN COMO STRING. Del otro lado son `Decimal` con
 * `decimal_places=2`, y un `number` de JavaScript no representa exactamente un
 * precio de ocho cifras con centavos. Mandarlo como texto deja que Python lo
 * parsee sin pasar por el flotante.
 *
 * ⚠️ LOS OPCIONALES VACÍOS SE OMITEN, no se mandan en `""`. El schema es
 * `extra="forbid"` y los campos son `str | None`: una cadena vacía pasaría el
 * tipo y quedaría guardada, y después "" no es ni un chasis ni un `null`.
 *
 * `tenant_id`, `status` y `assigned_user_id` NO ESTÁN, y no por omisión: el
 * tenant sale del token (regla dura 1), el estado inicial lo fija `RN-ST-04` y
 * la asignación es otra operación. El backend rechaza los tres con
 * `extra_forbidden` — verificado en vivo.
 */
export function aCuerpo(borrador: BorradorDeVehiculo): CuerpoDeAlta {
  const cuerpo: CuerpoDeAlta = {
    branch_id: borrador.branch_id,
    brand_id: borrador.brand_id,
    model_id: borrador.model_id,
    year: Number(borrador.year.trim()),
    mileage_km: Number(borrador.mileage_km.trim()),
    color: borrador.color.trim(),
    fuel_type: borrador.fuel_type,
    transmission: borrador.transmission,
    body_type: borrador.body_type,
    price_ars: borrador.price_ars.trim().replace(',', '.'),
  };

  const dominio = normalizarDominio(borrador.domain_plate);
  if (dominio !== null) cuerpo.domain_plate = dominio;

  const chasis = normalizarChasis(borrador.chassis_number);
  if (chasis !== null) cuerpo.chassis_number = chasis;

  if (borrador.engine_number.trim() !== '') {
    cuerpo.engine_number = borrador.engine_number.trim().toUpperCase();
  }
  if (borrador.price_usd.trim() !== '') {
    cuerpo.price_usd = borrador.price_usd.trim().replace(',', '.');
  }
  if (borrador.acquisition_cost_ars.trim() !== '') {
    cuerpo.acquisition_cost_ars = borrador.acquisition_cost_ars.trim().replace(',', '.');
  }
  if (borrador.description.trim() !== '') {
    cuerpo.description = borrador.description.trim();
  }

  return cuerpo;
}

// ── Los rechazos del backend, en castellano ─────────────────────────────────

/**
 * Los `code` que el `POST /vehicles` puede devolver.
 *
 * ⚠️ VERIFICADOS CONTRA EL BACKEND CORRIENDO el 21-ago-2026, no deducidos del
 * fuente. Es la segunda vez que se hace así en este módulo del frontend: la
 * primera versión de `cambiarEstado` tradujo `invalid_transition`, un código
 * que el backend nunca manda, y ese mensaje no se habría mostrado jamás sin que
 * nadie lo notara — el fallback genérico se ve razonable.
 *
 * ⚠️ `plan_quota_exceeded` es el ÚNICO que NO se reprodujo en vivo: haría falta
 * llenar la cuota de la agencia demo. Sale de `assert_can_add_vehicle`, que
 * `StockService.crear` llama antes de cualquier otra cosa.
 *
 * `domain_error` tenía una nota que ya se saldó: `VehiculoDuplicado` no
 * declaraba `code` propio y heredaba el genérico de `DomainError`, así que este
 * módulo lo traducía a "dominio repetido" POR DESCARTE —era el único
 * `DomainError` que el alta podía levantar—. Funcionaba y era frágil: un
 * segundo `DomainError` en el alta habría vuelto ese mensaje incorrecto en
 * silencio, diciéndole al usuario que repitió un dominio cuando el problema era
 * otro. El backend ahora declara `vehicle_duplicate` y la traducción es directa.
 *
 * Se siguen aceptando los dos por la ventana de despliegue; ver el test que lo
 * explica antes de sacar el viejo.
 */
const SIN_PERMISO = 'Tu rol no puede cargar vehículos. Pediselo a un gerente.';

/**
 * El `code` de `VehiculoDuplicado`, textual.
 *
 * Vive en una constante y no suelto en el `if` para que el guardián del backend
 * —`test_alta_espejada.py`— pueda leerlo con un `re` y compararlo contra el
 * atributo de la excepción, igual que hace con los enums y los regex. Un código
 * copiado a mano en los dos lados es exactamente la clase de espejo que se
 * desincroniza sin que nada se ponga rojo.
 */
export const DUPLICADO = 'vehicle_duplicate';

const MENSAJES_DE_ALTA: ReadonlyMap<string, string> = new Map([
  ['not_authenticated', 'Tu sesión venció. Volvé a iniciar sesión.'],
  ['insufficient_permission', SIN_PERMISO],
  ['insufficient_role', SIN_PERMISO],
  // 402 y no 403, y la diferencia importa: ningún permiso arregla una cuota
  // llena. Mandar a pedir permisos sería mandar al lugar equivocado.
  [
    'plan_quota_exceeded',
    'Tu plan llegó al techo de vehículos. Para cargar más hay que subir de plan.',
  ],
]);

/**
 * El mensaje de un rechazo, o `null` si no lo conocemos.
 *
 * Devuelve `null` en vez de inventar un texto: quien llama arma el fallback con
 * el estado HTTP, que al menos es cierto. Un mensaje traducido de más miente
 * con cara de estar bien, y nadie lo revisa porque se ve razonable.
 *
 * `validation_error` NO se traduce a propósito. Significa que un campo puntual
 * está mal, y `validar` ya lo atrapa antes de mandar: si llega igual es que las
 * dos validaciones divergieron, y un mensaje amable escondería justo el síntoma
 * que hace falta ver.
 */
export function mensajeDeAlta(codigo: string, status: number): string | null {
  // `domain_error` depende del estado: es genérico, y solo en un 422 del alta
  // significa `RN-ST-01`. `vehicle_duplicate` no lo necesita —nombra la regla—
  // pero se acepta igual mientras dure la ventana de despliegue.
  if (codigo === DUPLICADO || (codigo === 'domain_error' && status === 422)) {
    return 'Ya hay un vehículo cargado con ese dominio.';
  }
  return MENSAJES_DE_ALTA.get(codigo) ?? null;
}
