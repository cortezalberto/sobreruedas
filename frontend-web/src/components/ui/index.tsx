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
 *   7. Campo          — texto con etiqueta y error accesible          [pendiente]
 *   8. Seleccion      — desplegable, base del selector en cascada     [pendiente]
 *   9. Casilla        — booleano                                      [pendiente]
 *  10. Tabla          — listados densos con encabezado fijo           [pendiente]
 *  11. Modal          — el brand book lo EXIGE para el destructivo    [pendiente]
 *  12. Migas          — navegacion jerarquica                         [pendiente]
 *  13. Paginacion     — sobre el cursor que ya expone el backend      [pendiente]
 *
 * Los seis primeros son los que las pantallas existentes ya piden. Los otros
 * siete se implementan cuando exista la pantalla que los use: un primitivo sin
 * consumidor se disena a ciegas y se termina reescribiendo.
 *
 * ⚠️ NO HAY LIBRERIA DE COMPONENTES. El stack declara Radix UI, y entra cuando
 * haga falta comportamiento accesible dificil de escribir a mano —foco atrapado
 * en el modal, navegacion por teclado del desplegable—. Un boton y una tarjeta
 * no lo necesitan, y traer la dependencia para eso agrega superficie sin
 * comprar nada.
 */
import type { ReactNode } from 'react';

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
    <div
      className={`rounded-lg border border-neutro-borde p-4 ${
        interactiva ? 'hover:border-marca' : ''
      }`}
    >
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
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse rounded-lg border border-neutro-borde ${alto}`}
    />
  );
}
