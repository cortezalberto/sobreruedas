/**
 * Primitivos del design system — C-07, `T-037`. Cierra el riesgo `R-4`.
 *
 * LA LISTA DE 13 NO EXISTE EN NINGUN DOCUMENTO, Y HABIA QUE DEFINIRLA
 * ───────────────────────────────────────────────────────────────────
 * El plan de implementacion menciona "13 componentes UI primitivos" **sin
 * enumerarlos**, y el brand book especifica 8 piezas visuales que no son la
 * misma lista (`knowledge-base/15` §Componentes UI, §122). Eso es `R-4`.
 *
 * La lista se deriva de lo que las pantallas del roadmap necesitan de verdad, no
 * de un catalogo generico:
 *
 *   1. Boton          — primario / secundario / destructivo (brand book)
 *   2. Alerta         — exito / advertencia / error / meta
 *   3. Tarjeta        — contenedor con borde, base de las grillas
 *   4. Etiqueta       — estado de un registro (vehiculo, lead, agencia)
 *   5. EstadoVacio    — "no hay nada todavia" + accion (brand book)
 *   6. Esqueleto      — carga, ya usado por los `loading.tsx`
 *   7. Seleccion      — desplegable, base del selector en cascada
 *   8. Migas          — navegacion jerarquica
 *   9. Tabla          — listados densos
 *  10. Modal          — panel de ayuda; el brand book lo EXIGE para el destructivo
 *  11. Campo          — texto con etiqueta y error accesible          [pendiente]
 *  12. Casilla        — booleano                                      [pendiente]
 *  13. Paginacion     — sobre el cursor que ya expone el backend      [pendiente]
 *
 * Los tres pendientes esperan una pantalla que los use: `Campo` y `Casilla`
 * necesitan formularios —y no hay formularios hasta que haya identidad—, y
 * `Paginacion` necesita un listado que no entre en una pantalla. Un primitivo
 * sin consumidor se disena a ciegas y se termina reescribiendo.
 *
 * RADIX ENTRA SOLO EN EL MODAL. El stack lo declara, y el criterio para usarlo
 * es que haga falta comportamiento accesible dificil de escribir a mano. Un
 * boton, una tarjeta y un `<select>` nativo no lo necesitan. Un dialogo SI:
 * atrapar el foco, devolverlo al cerrar, inertizar el fondo y cerrar con `Esc`
 * son cuatro cosas que se implementan mal casi siempre.
 */
'use client';

import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

// Las superficies viven en `lib/tokens` y NO acá. Este modulo es `'use client'`,
// y una constante exportada desde un modulo cliente le llega a un Server
// Component como referencia al cliente, no como string. Ver el encabezado de
// `SUPERFICIE_DE_TARJETA`.
import { REALCE_DE_TARJETA, SUPERFICIE_DE_TARJETA } from '@/lib/tokens';

// ── 1. Boton ────────────────────────────────────────────────────────────────

type VarianteDeBoton = 'primario' | 'secundario' | 'destructivo';

/**
 * `switch` y no un objeto indexado, en los cuatro mapeos de este archivo.
 *
 * Dos motivos. TypeScript verifica que el `switch` cubra la union entera, asi
 * que agregar una variante sin darle estilo no compila — con un `Record` se
 * puede olvidar una clave y salir `undefined` en pantalla. Y `eslint-plugin-security`
 * marca todo acceso por indice como inyeccion de objeto: acá es falso positivo
 * —la clave es de tipo union, no entrada del usuario— pero cuatro advertencias
 * permanentes son cuatro advertencias que alguien va a terminar apagando.
 */
function estiloDeBoton(variante: VarianteDeBoton): string {
  switch (variante) {
    case 'primario':
      return 'bg-marca text-white hover:opacity-90';
    case 'secundario':
      return 'border border-marca text-marca bg-white hover:bg-neutro-fondo';
    case 'destructivo':
      return 'bg-estado-error text-white hover:opacity-90';
  }
}

interface PropsDeBoton {
  children: ReactNode;
  variante?: VarianteDeBoton;
  type?: 'button' | 'submit';
  onClick?: () => void;
  disabled?: boolean;
}

/**
 * ⚠️ El brand book exige que el destructivo pida confirmacion en un modal.
 * Este componente NO la impone: no puede: el modal es el primitivo 11 y todavia
 * no existe. Queda dicho acá para que quien monte el primer destructivo real no
 * lo de por resuelto.
 *
 * `type="button"` por defecto y no `submit`: el default del HTML es `submit`, y
 * un boton suelto dentro de un formulario que lo envia sin querer es de los
 * errores mas dificiles de ver leyendo el JSX.
 */
export function Boton({
  children,
  variante = 'primario',
  type = 'button',
  onClick,
  disabled,
}: PropsDeBoton) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-md px-3 py-1.5 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50 ${estiloDeBoton(variante)}`}
    >
      {children}
    </button>
  );
}

// ── 2. Alerta ───────────────────────────────────────────────────────────────

type TonoDeAlerta = 'exito' | 'advertencia' | 'error' | 'meta';

function estilosDeAlerta(tono: TonoDeAlerta): { borde: string; texto: string } {
  switch (tono) {
    case 'exito':
      return { borde: 'border-estado-exito', texto: 'text-estado-exito' };
    case 'advertencia':
      return { borde: 'border-estado-advertencia', texto: 'text-estado-advertencia' };
    case 'error':
      return { borde: 'border-estado-error', texto: 'text-estado-error' };
    case 'meta':
      return { borde: 'border-estado-meta', texto: 'text-estado-meta' };
  }
}

/**
 * ⚠️ `role="alert"` SOLO para error y advertencia.
 *
 * `alert` interrumpe al lector de pantalla en el momento. Para una confirmacion
 * de exito eso es ruido: se anuncia con `status`, que espera a que el usuario
 * termine lo que esta leyendo. Ponerle `alert` a todo hace que la gente apague
 * el lector, que es lo contrario de accesible.
 *
 * El TITULO es obligatorio y no decorativo: es el canal de texto que WCAG 1.4.1
 * exige junto al color. Una alerta que solo se distingue por el borde no cumple
 * para quien no diferencia rojo de naranja — que es justo el par de estados.
 */
export function Alerta({
  tono,
  titulo,
  children,
}: {
  tono: TonoDeAlerta;
  titulo: string;
  children?: ReactNode;
}) {
  const urgente = tono === 'error' || tono === 'advertencia';
  const estilos = estilosDeAlerta(tono);

  return (
    <div
      role={urgente ? 'alert' : 'status'}
      className={`rounded-lg border-l-4 bg-neutro-fondo p-4 ${estilos.borde}`}
    >
      <p className={`font-medium ${estilos.texto}`}>{titulo}</p>
      {children && <div className="mt-1 text-sm text-neutro-texto">{children}</div>}
    </div>
  );
}

// ── 3. Tarjeta ──────────────────────────────────────────────────────────────

/**
 * `interactiva` cambia el borde al pasar el mouse, y nada mas. NO agrega
 * `onClick`: una tarjeta clickeable entera no es alcanzable por teclado ni
 * anunciable por un lector. Lo que va adentro es un `<Link>` o un `<button>`
 * de verdad, y la tarjeta solo lo envuelve.
 */
export function Tarjeta({
  children,
  interactiva = false,
}: {
  children: ReactNode;
  interactiva?: boolean;
}) {
  return (
    <div className={`${SUPERFICIE_DE_TARJETA} p-4 ${interactiva ? REALCE_DE_TARJETA : ''}`}>
      {children}
    </div>
  );
}

// ── 4. Etiqueta ─────────────────────────────────────────────────────────────

type TonoDeEtiqueta = 'neutro' | 'exito' | 'advertencia' | 'error' | 'meta';

function estiloDeEtiqueta(tono: TonoDeEtiqueta): string {
  switch (tono) {
    case 'neutro':
      return 'border-neutro-borde text-neutro-texto';
    case 'exito':
      return 'border-estado-exito text-estado-exito';
    case 'advertencia':
      return 'border-estado-advertencia text-estado-advertencia';
    case 'error':
      return 'border-estado-error text-estado-error';
    case 'meta':
      return 'border-estado-meta text-estado-meta';
  }
}

/**
 * Estado de un registro: activo, en trial, vendido, perdido.
 *
 * Contorno y no relleno: un relleno saturado en tamano chico obliga a texto
 * blanco, y el blanco sobre estos tonos oscuros pasa AA justo. Con contorno el
 * texto va sobre blanco y el contraste es el mismo que audita `T-038`.
 */
export function Etiqueta({
  tono = 'neutro',
  children,
}: {
  tono?: TonoDeEtiqueta;
  children: ReactNode;
}) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 text-xs font-medium ${estiloDeEtiqueta(tono)}`}
    >
      {children}
    </span>
  );
}

// ── 5. EstadoVacio ──────────────────────────────────────────────────────────

/**
 * El brand book pide "ilustracion isometrica + CTA". La ilustracion no existe
 * —no hay assets en el corpus— asi que se deja el hueco sin inventar un dibujo.
 * Lo que si esta es el CTA, que es la parte funcional: un vacio sin salida deja
 * al usuario sin saber que hacer.
 */
export function EstadoVacio({
  titulo,
  descripcion,
  accion,
}: {
  titulo: string;
  descripcion?: string;
  accion?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-dashed border-neutro-borde p-8 text-center">
      <p className="font-medium text-neutro-enfasis">{titulo}</p>
      {descripcion && (
        <p className="mx-auto mt-1 max-w-lectura text-sm text-neutro-texto">{descripcion}</p>
      )}
      {accion && <div className="mt-4">{accion}</div>}
    </div>
  );
}

// ── 6. Esqueleto ────────────────────────────────────────────────────────────

/**
 * `aria-hidden` a proposito: la animacion no dice nada a un lector de pantalla.
 * Quien anuncia la espera es el contenedor, con `aria-busy` y un texto para
 * lectores — ver los `loading.tsx`. Un esqueleto que se lee en voz alta es una
 * ristra de nada.
 */
export function Esqueleto({ alto = 'h-24' }: { alto?: string }) {
  return <div aria-hidden="true" className={`animate-pulse ${SUPERFICIE_DE_TARJETA} ${alto}`} />;
}

// ── 7. Seleccion ────────────────────────────────────────────────────────────

/**
 * Desplegable con etiqueta asociada.
 *
 * La etiqueta va con `htmlFor` y no envolviendo al control: las dos formas son
 * validas en HTML, pero la asociacion explicita es la unica que sobrevive a que
 * alguien reordene el JSX. Sin etiqueta asociada, un lector de pantalla anuncia
 * "combo box" y nada mas.
 *
 * `<select>` nativo y no un desplegable propio. El nativo ya trae teclado,
 * busqueda por letra y el selector de rueda del telefono — reimplementarlo es
 * exactamente el trabajo para el que existe Radix, y todavia no hace falta.
 */
export function Seleccion({
  id,
  etiqueta,
  valor,
  alCambiar,
  opciones,
  deshabilitado,
  textoVacio = 'Elegí una opción',
}: {
  id: string;
  etiqueta: string;
  valor: string;
  alCambiar: (valor: string) => void;
  opciones: readonly { valor: string; texto: string }[];
  deshabilitado?: boolean;
  textoVacio?: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-neutro-texto">
        {etiqueta}
      </label>
      <select
        id={id}
        value={valor}
        disabled={deshabilitado}
        onChange={(evento) => alCambiar(evento.target.value)}
        className="mt-1 w-full rounded-md border border-neutro-borde bg-white px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-50"
      >
        <option value="">{textoVacio}</option>
        {opciones.map((opcion) => (
          <option key={opcion.valor} value={opcion.valor}>
            {opcion.texto}
          </option>
        ))}
      </select>
    </div>
  );
}

// ── 8. Migas ────────────────────────────────────────────────────────────────

/**
 * Navegacion jerarquica.
 *
 * El ultimo tramo NO es un enlace: es donde ya estas, y un enlace a la pagina
 * actual es ruido para quien tabula. Se marca con `aria-current="page"`, que es
 * lo que un lector anuncia.
 *
 * El `<nav>` lleva nombre porque una pagina puede tener varias navegaciones
 * —la principal y esta— y sin nombre se anuncian las dos igual.
 */
export function Migas({ tramos }: { tramos: readonly { texto: string; href?: string }[] }) {
  return (
    <nav aria-label="Migas de navegación">
      <ol className="flex flex-wrap items-center gap-2 text-sm text-neutro-texto">
        {tramos.map((tramo, posicion) => (
          <li key={tramo.texto} className="flex items-center gap-2">
            {posicion > 0 && <span aria-hidden="true">/</span>}
            {tramo.href ? (
              <a href={tramo.href} className="underline underline-offset-4 hover:text-marca">
                {tramo.texto}
              </a>
            ) : (
              <span aria-current="page" className="text-neutro-enfasis">
                {tramo.texto}
              </span>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

// ── 9. Tabla ────────────────────────────────────────────────────────────────

/**
 * Listado denso.
 *
 * `<caption>` obligatorio y visualmente oculto: es lo que le dice a un lector de
 * pantalla de que es esta tabla antes de leer 50 filas. Es la diferencia entre
 * "tabla, 6 columnas" y "modelos de Toyota, tabla, 6 columnas".
 *
 * `scope="col"` en los encabezados: sin eso, el lector no sabe que celda
 * encabeza que columna y lee los datos sueltos.
 */
export function Tabla({
  descripcion,
  columnas,
  children,
}: {
  descripcion: string;
  columnas: readonly string[];
  children: ReactNode;
}) {
  return (
    // El contenedor scrollea en horizontal: una tabla ancha en un telefono
    // rompe el ancho del documento entero si no se acota acá.
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{descripcion}</caption>
        <thead>
          <tr className="border-b border-neutro-borde text-left">
            {columnas.map((columna) => (
              <th key={columna} scope="col" className="py-2 pr-4 font-medium text-neutro-texto">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  );
}

// ── 10. Modal ───────────────────────────────────────────────────────────────

/**
 * Dialogo modal, sobre Radix.
 *
 * ES LA UNICA PIEZA DE ESTE ARCHIVO QUE USA UNA LIBRERIA, y el criterio esta en
 * el encabezado: un dialogo accesible exige atrapar el foco adentro, devolverlo
 * al elemento que lo abrio, inertizar el fondo para los lectores de pantalla y
 * cerrar con `Esc`. Son cuatro cosas que se implementan mal casi siempre, y
 * ninguna se ve rota hasta que alguien navega con teclado.
 *
 * El titulo es obligatorio: Radix lo usa como nombre accesible del dialogo. Sin
 * el, un lector anuncia "dialogo" y nada mas — y ademas Radix avisa en consola,
 * asi que omitirlo es ruido garantizado.
 *
 * `Esc` lo maneja Radix. Es el atajo que `knowledge-base/06` pide para cerrar
 * modales, y no hace falta cablearlo aparte.
 */
export function Modal({
  abierto,
  alCerrar,
  titulo,
  descripcion,
  children,
}: {
  abierto: boolean;
  alCerrar: () => void;
  titulo: string;
  descripcion?: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={abierto} onOpenChange={(sigueAbierto) => !sigueAbierto && alCerrar()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-neutro-enfasis/40" />
        <Dialog.Content
          className={`fixed left-1/2 top-1/2 w-[min(32rem,90vw)] -translate-x-1/2 -translate-y-1/2 bg-white p-6 shadow-lg ${SUPERFICIE_DE_TARJETA}`}
        >
          <Dialog.Title className="text-lg font-semibold tracking-tight">{titulo}</Dialog.Title>
          {descripcion && (
            <Dialog.Description className="mt-1 text-sm text-neutro-texto">
              {descripcion}
            </Dialog.Description>
          )}
          <div className="mt-4">{children}</div>
          <div className="mt-6 flex justify-end">
            <Dialog.Close asChild>
              <Boton variante="secundario">Cerrar</Boton>
            </Dialog.Close>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
