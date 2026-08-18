/**
 * Selector en cascada marca → modelo — C-13.
 *
 * Es el item de alcance de C-13 que decia "componente de selector en cascada
 * `brand → model → version`". Llega hasta MODELO: `vehicle_versions` no existe
 * todavia, y su seed depende de que los modelos esten curados (ver la migracion
 * `009`). El tercer nivel se agrega cuando exista la tabla.
 *
 * ES CLIENT COMPONENT, Y ACA SI HACE FALTA. Las paginas del catalogo son Server
 * Components porque solo leen. Esto tiene estado que cambia con el usuario y
 * pide datos DESPUES del primer render: elegir una marca dispara la carga de sus
 * modelos. Eso no se puede hacer en el servidor.
 *
 * ⚠️ NO usa TanStack Query todavia, y es deliberado. La libreria compra cache,
 * reintentos y deduplicacion; acá hay UNA peticion por cambio de marca sobre un
 * catalogo que no cambia. Entra cuando haya varias vistas compartiendo datos que
 * si cambian —el stock, los leads—, no antes.
 */
'use client';

import { useEffect, useState } from 'react';

import { obtenerModelos, type Marca, type Modelo } from '@/lib/api';

import { Alerta, Seleccion } from './ui';

export function SelectorDeVehiculo({ marcas }: { marcas: readonly Marca[] }) {
  const [marca, setMarca] = useState('');
  const [modelo, setModelo] = useState('');
  const [modelos, setModelos] = useState<readonly Modelo[]>([]);
  const [cargando, setCargando] = useState(false);
  const [fallo, setFallo] = useState(false);

  /**
   * Los reinicios viven ACA y no en el efecto.
   *
   * Hacer `setState` sincrono dentro de un `useEffect` dispara renders en
   * cascada, y React 19 lo marca como error. Ademas es lo correcto
   * conceptualmente: limpiar el modelo elegido es consecuencia inmediata de que
   * el usuario cambio de marca, no de que un dato externo haya cambiado. El
   * efecto queda para lo unico que es: hablar con la red.
   */
  function alElegirMarca(nueva: string): void {
    setMarca(nueva);
    setModelo('');
    setModelos([]);
    setFallo(false);
    setCargando(nueva !== '');
  }

  useEffect(() => {
    if (!marca) return;

    // `cancelado` evita la condicion de carrera clasica de este componente: si
    // alguien cambia de marca dos veces rapido, la primera respuesta puede
    // llegar DESPUES de la segunda y pisar la lista con los modelos de la marca
    // equivocada. El efecto se limpia y descarta lo que ya no corresponde.
    let cancelado = false;

    obtenerModelos(marca)
      .then((recibidos) => {
        if (!cancelado) setModelos(recibidos);
      })
      .catch(() => {
        if (!cancelado) setFallo(true);
      })
      .finally(() => {
        if (!cancelado) setCargando(false);
      });

    return () => {
      cancelado = true;
    };
  }, [marca]);

  const elegido = modelos.find((m) => m.id === modelo);

  return (
    <div className="space-y-4">
      <Seleccion
        id="marca"
        etiqueta="Marca"
        valor={marca}
        alCambiar={alElegirMarca}
        textoVacio="Elegí una marca"
        // El VALOR es el id porque es lo que el backend pide; el slug solo vive
        // en las URLs del frontend.
        opciones={marcas.map((m) => ({ valor: m.id, texto: m.name }))}
      />

      <Seleccion
        id="modelo"
        etiqueta="Modelo"
        valor={modelo}
        alCambiar={setModelo}
        // Deshabilitado sin marca y mientras carga. El texto cambia en vez de
        // quedar en "Elegí un modelo" sobre una lista vacia, que se lee como si
        // la marca no tuviera ninguno.
        deshabilitado={!marca || cargando}
        textoVacio={!marca ? 'Elegí una marca primero' : cargando ? 'Cargando…' : 'Elegí un modelo'}
        opciones={modelos.map((m) => ({
          valor: m.id,
          texto: `${m.name} · ${m.body_type}`,
        }))}
      />

      {fallo && (
        <Alerta tono="error" titulo="No se pudieron cargar los modelos">
          Probá elegir la marca de nuevo.
        </Alerta>
      )}

      {elegido && (
        <p className="text-sm text-neutro-texto">
          Seleccionado: <strong className="text-neutro-enfasis">{elegido.name}</strong> ·{' '}
          {elegido.body_type} · desde {elegido.year_from}
          {elegido.year_to === null ? ', vigente' : ` hasta ${elegido.year_to}`}
        </p>
      )}
    </div>
  );
}
