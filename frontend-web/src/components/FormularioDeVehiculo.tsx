'use client';

/**
 * El alta de un vehículo — lo que faltaba de la rebanada vertical de `ESC-003`.
 *
 * CLIENT COMPONENT, y acá hace falta de verdad: tiene estado que cambia con
 * cada tecla y pide datos DESPUÉS del primer render — elegir una marca dispara
 * la carga de sus modelos. Nada de eso se puede hacer en el servidor.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * NO DECIDE PERMISOS
 * ─────────────────────────────────────────────────────────────────────────
 * No hay ningún `if (rol === 'manager')` acá, y su ausencia es deliberada. Un
 * `salesperson` puede llegar a esta pantalla, completarla y recibir un 403
 * —verificado en vivo contra el backend—. Eso es lo correcto: la única copia de
 * la matriz que existe es `rbac.py`, y una segunda en el cliente sería editable
 * con las herramientas del navegador. Misma decisión que `CambiarEstado`.
 *
 * ─────────────────────────────────────────────────────────────────────────
 * POR QUÉ VALIDA ANTES DE MANDAR
 * ─────────────────────────────────────────────────────────────────────────
 * No por ahorrarle una petición al backend. Porque hay errores que el backend
 * NO sabe atribuir a un campo: el dominio mal formado y el "sin dominio ni
 * chasis" salen los dos con `field: "body"`, porque los valida un
 * `model_validator(mode="after")` de Pydantic. En un formulario de catorce
 * campos, "hay algo mal" sin decir dónde es lo mismo que no decir nada.
 *
 * Las reglas viven en `lib/vehiculo-nuevo.ts`, no acá: se prueban sin montar
 * React, y este archivo queda con lo que solo existe montado.
 */

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { crearVehiculo } from '@/app/stock/acciones';
import { Alerta, Boton, Campo, Seleccion } from '@/components/ui';
import { obtenerModelos, type Marca, type Modelo, type Sucursal } from '@/lib/api';
import {
  aCuerpo,
  BORRADOR_VACIO,
  CARROCERIAS,
  COMBUSTIBLES,
  TRANSMISIONES,
  validar,
  type BorradorDeVehiculo,
  type ErroresDelBorrador,
} from '@/lib/vehiculo-nuevo';

/**
 * Los errores, sin los campos indicados.
 *
 * Se filtra por clave en vez de desestructurar-y-descartar (`const { [campo]:
 * _, ...resto }`): esa forma deja variables sin usar que el linter marca, y la
 * marca tiene razon en el caso general — una variable sin usar suele ser un
 * olvido, no una intencion.
 *
 * Devuelve el MISMO objeto cuando no hay nada que sacar. Sin eso, cada tecla
 * crearia un objeto nuevo y React volveria a renderizar el formulario entero
 * aunque los errores no hayan cambiado.
 */
function sinLosCampos(
  errores: ErroresDelBorrador,
  ...campos: readonly (keyof BorradorDeVehiculo)[]
): ErroresDelBorrador {
  if (!campos.some((campo) => campo in errores)) return errores;

  const quitar = new Set<string>(campos);
  return Object.fromEntries(
    Object.entries(errores).filter(([clave]) => !quitar.has(clave)),
  ) as ErroresDelBorrador;
}

export function FormularioDeVehiculo({
  sucursales,
  marcas,
}: {
  sucursales: readonly Sucursal[];
  marcas: readonly Marca[];
}) {
  const router = useRouter();

  const [borrador, setBorrador] = useState<BorradorDeVehiculo>(BORRADOR_VACIO);
  const [errores, setErrores] = useState<ErroresDelBorrador>({});
  const [rechazo, setRechazo] = useState<string | null>(null);
  const [enCurso, setEnCurso] = useState(false);

  const [modelos, setModelos] = useState<readonly Modelo[]>([]);
  const [cargandoModelos, setCargandoModelos] = useState(false);
  const [falloElCatalogo, setFalloElCatalogo] = useState(false);

  /**
   * Escribir en un campo LIMPIA su error, no revalida todo.
   *
   * Revalidar el formulario entero en cada tecla haría aparecer errores en
   * campos que el usuario todavía no tocó — "poné el precio" mientras recién va
   * por la marca. Los errores aparecen al intentar guardar; escribir solo borra
   * el del campo que se está corrigiendo.
   *
   * Y borrarlo importa: dejar el rojo puesto sobre algo ya arreglado entrena a
   * ignorar el rojo, y después el error que sí importa tampoco se ve.
   */
  function escribir(campo: keyof BorradorDeVehiculo, valor: string): void {
    setBorrador((previo) => ({ ...previo, [campo]: valor }));
    setErrores((previos) => sinLosCampos(previos, campo));
    setRechazo(null);
  }

  /**
   * Los reinicios van acá y no en el efecto — igual que en `SelectorDeVehiculo`.
   *
   * Un `setState` síncrono dentro de un `useEffect` dispara renders en cascada
   * y React 19 lo marca. Además es lo correcto: olvidar el modelo es
   * consecuencia inmediata de cambiar de marca, no de que llegó un dato.
   *
   * Y olvidarlo hace falta: un modelo de la marca anterior con la marca nueva
   * es un par que no existe, y el backend lo aceptaría sin chistar porque son
   * dos ids sueltos que no se validan entre sí.
   */
  function elegirMarca(marcaId: string): void {
    setBorrador((previo) => ({ ...previo, brand_id: marcaId, model_id: '' }));
    setErrores((previos) => sinLosCampos(previos, 'brand_id', 'model_id'));
    setModelos([]);
    setFalloElCatalogo(false);
    setCargandoModelos(marcaId !== '');
  }

  useEffect(() => {
    if (!borrador.brand_id) return;

    // Misma carrera que en `SelectorDeVehiculo`: dos cambios rápidos de marca
    // pueden volver en orden inverso y pisar la lista con los modelos de la
    // marca equivocada.
    let cancelado = false;

    obtenerModelos(borrador.brand_id)
      .then((recibidos) => {
        if (!cancelado) setModelos(recibidos);
      })
      .catch(() => {
        if (!cancelado) setFalloElCatalogo(true);
      })
      .finally(() => {
        if (!cancelado) setCargandoModelos(false);
      });

    return () => {
      cancelado = true;
    };
  }, [borrador.brand_id]);

  async function guardar(): Promise<void> {
    // El guard del doble clic va ANTES de todo: un `disabled` en el botón
    // llega un render tarde, y en ese hueco entra el segundo clic. Sin esto se
    // cargan dos vehículos y el segundo choca contra `RN-ST-01`, así que el
    // usuario ve un error de duplicado por un auto que cargó una sola vez.
    if (enCurso) return;

    const encontrados = validar(borrador);
    setErrores(encontrados);
    if (Object.keys(encontrados).length > 0) {
      setRechazo(null);
      return;
    }

    setEnCurso(true);
    setRechazo(null);
    try {
      const resultado = await crearVehiculo(aCuerpo(borrador));

      if (resultado.ok) {
        router.push('/stock');
        return;
      }
      // El borrador NO se limpia. El rechazo no es culpa del formulario —un
      // 403, un dominio repetido, la cuota del plan— y perder catorce campos
      // por algo que el usuario no puede prever es inaceptable.
      setRechazo(resultado.mensaje);
    } finally {
      setEnCurso(false);
    }
  }

  const hayErrores = Object.keys(errores).length > 0;

  return (
    <form
      noValidate
      onSubmit={(evento) => {
        // `noValidate` apaga la validación nativa del navegador a propósito: sus
        // globos son intraducibles, se ven distinto en cada navegador y no
        // conocen `ADR-031`. La validación de verdad es la nuestra.
        evento.preventDefault();
        void guardar();
      }}
      className="space-y-6"
    >
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutro-texto">
          Dónde está y qué es
        </h2>

        <Seleccion
          id="branch_id"
          etiqueta="Sucursal"
          valor={borrador.branch_id}
          alCambiar={(valor) => escribir('branch_id', valor)}
          textoVacio="Elegí la sucursal"
          opciones={sucursales.map((s) => ({ valor: s.id, texto: `${s.name} · ${s.city}` }))}
        />
        {errores.branch_id && (
          <p role="alert" className="text-xs text-estado-error">
            {errores.branch_id}
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <Seleccion
              id="brand_id"
              etiqueta="Marca"
              valor={borrador.brand_id}
              alCambiar={elegirMarca}
              textoVacio="Elegí una marca"
              opciones={marcas.map((m) => ({ valor: m.id, texto: m.name }))}
            />
            {errores.brand_id && (
              <p role="alert" className="mt-1 text-xs text-estado-error">
                {errores.brand_id}
              </p>
            )}
          </div>

          <div>
            <Seleccion
              id="model_id"
              etiqueta="Modelo"
              valor={borrador.model_id}
              alCambiar={(valor) => escribir('model_id', valor)}
              deshabilitado={!borrador.brand_id || cargandoModelos}
              textoVacio={
                !borrador.brand_id
                  ? 'Elegí una marca primero'
                  : cargandoModelos
                    ? 'Cargando…'
                    : 'Elegí un modelo'
              }
              opciones={modelos.map((m) => ({ valor: m.id, texto: m.name }))}
            />
            {errores.model_id && (
              <p role="alert" className="mt-1 text-xs text-estado-error">
                {errores.model_id}
              </p>
            )}
          </div>
        </div>

        {falloElCatalogo && (
          <Alerta tono="error" titulo="No se pudieron cargar los modelos">
            Probá elegir la marca de nuevo.
          </Alerta>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutro-texto">
          Cómo se identifica
        </h2>

        {/* `ADR-031`: los dos son opcionales por separado y obligatorio uno de
            los dos. Van juntos y con la ayuda escrita para que se lea como una
            sola decisión y no como dos campos que se pueden saltear. */}
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo
            id="domain_plate"
            etiqueta="Dominio"
            opcional
            valor={borrador.domain_plate}
            alCambiar={(valor) => escribir('domain_plate', valor)}
            error={errores.domain_plate}
            placeholder="AB123CD"
            ayuda="Un 0 km sin patentar todavía no tiene."
          />
          <Campo
            id="chassis_number"
            etiqueta="Número de chasis"
            opcional
            valor={borrador.chassis_number}
            alCambiar={(valor) => escribir('chassis_number', valor)}
            error={errores.chassis_number}
            ayuda="17 caracteres. Hace falta el dominio o este."
          />
        </div>

        <Campo
          id="engine_number"
          etiqueta="Número de motor"
          opcional
          valor={borrador.engine_number}
          alCambiar={(valor) => escribir('engine_number', valor)}
          error={errores.engine_number}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutro-texto">
          El vehículo
        </h2>

        <div className="grid gap-4 sm:grid-cols-3">
          <Campo
            id="year"
            etiqueta="Año"
            tipo="number"
            valor={borrador.year}
            alCambiar={(valor) => escribir('year', valor)}
            error={errores.year}
          />
          <Campo
            id="mileage_km"
            etiqueta="Kilómetros"
            tipo="number"
            valor={borrador.mileage_km}
            alCambiar={(valor) => escribir('mileage_km', valor)}
            error={errores.mileage_km}
          />
          <Campo
            id="color"
            etiqueta="Color"
            valor={borrador.color}
            alCambiar={(valor) => escribir('color', valor)}
            error={errores.color}
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <Seleccion
              id="fuel_type"
              etiqueta="Combustible"
              valor={borrador.fuel_type}
              alCambiar={(valor) => escribir('fuel_type', valor)}
              opciones={COMBUSTIBLES}
            />
            {errores.fuel_type && (
              <p role="alert" className="mt-1 text-xs text-estado-error">
                {errores.fuel_type}
              </p>
            )}
          </div>
          <div>
            <Seleccion
              id="transmission"
              etiqueta="Transmisión"
              valor={borrador.transmission}
              alCambiar={(valor) => escribir('transmission', valor)}
              opciones={TRANSMISIONES}
            />
            {errores.transmission && (
              <p role="alert" className="mt-1 text-xs text-estado-error">
                {errores.transmission}
              </p>
            )}
          </div>
          <div>
            <Seleccion
              id="body_type"
              etiqueta="Carrocería"
              valor={borrador.body_type}
              alCambiar={(valor) => escribir('body_type', valor)}
              opciones={CARROCERIAS}
            />
            {errores.body_type && (
              <p role="alert" className="mt-1 text-xs text-estado-error">
                {errores.body_type}
              </p>
            )}
          </div>
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-neutro-texto">Plata</h2>

        <div className="grid gap-4 sm:grid-cols-3">
          <Campo
            id="price_ars"
            etiqueta="Precio de venta (ARS)"
            valor={borrador.price_ars}
            alCambiar={(valor) => escribir('price_ars', valor)}
            error={errores.price_ars}
          />
          <Campo
            id="price_usd"
            etiqueta="Precio en USD"
            opcional
            valor={borrador.price_usd}
            alCambiar={(valor) => escribir('price_usd', valor)}
            error={errores.price_usd}
          />
          {/* `RN-ST-12`: a un vendedor el backend ni siquiera le manda este
              campo al listar. Acá se ofrece igual — si su rol no puede
              escribirlo, el 403 lo dice el backend, no esta pantalla. */}
          <Campo
            id="acquisition_cost_ars"
            etiqueta="Precio de costo (ARS)"
            opcional
            valor={borrador.acquisition_cost_ars}
            alCambiar={(valor) => escribir('acquisition_cost_ars', valor)}
            error={errores.acquisition_cost_ars}
          />
        </div>
      </section>

      <Campo
        id="description"
        etiqueta="Descripción"
        opcional
        valor={borrador.description}
        alCambiar={(valor) => escribir('description', valor)}
        error={errores.description}
      />

      {hayErrores && (
        <Alerta tono="advertencia" titulo="Faltan datos">
          Revisá los campos marcados en rojo.
        </Alerta>
      )}

      {rechazo && (
        <Alerta tono="error" titulo="No se pudo cargar el vehículo">
          {rechazo}
        </Alerta>
      )}

      <div className="flex items-center gap-3">
        <Boton type="submit" disabled={enCurso}>
          {enCurso ? 'Cargando…' : 'Cargar vehículo'}
        </Boton>
        <Boton variante="secundario" onClick={() => router.push('/stock')} disabled={enCurso}>
          Cancelar
        </Boton>
      </div>
    </form>
  );
}
