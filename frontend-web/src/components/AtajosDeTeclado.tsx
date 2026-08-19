/**
 * Atajos de teclado del producto — C-07.
 *
 * `knowledge-base/06` §279 define diez: `G+D` Dashboard · `G+S` Stock · `G+L`
 * Leads · `G+M` Mensajes · `G+R` Reportes · `Ctrl+K` buscador global · `Ctrl+N`
 * crear nuevo · `Ctrl+S` guardar · `Esc` cerrar modal · `?` ayuda.
 *
 * ⚠️ SE IMPLEMENTAN TRES, Y NO ES UN RECORTE ARBITRARIO.
 *
 * Siete de esos diez apuntan a secciones que NO EXISTEN todavia —Dashboard,
 * Stock, Leads, Mensajes, Reportes— o a acciones que no hay como hacer —crear,
 * guardar, buscar—. Cablearlos ahora daria un atajo que lleva a un 404 o que no
 * hace nada, que es exactamente el error que este proyecto ya se marco solo
 * cuando la home prometia un `/login` inexistente: "un redirect a una ruta que
 * no existe seria un 404 disfrazado de feature".
 *
 * Lo que SI entra es el mecanismo completo y los atajos que tienen destino:
 *
 *   `?`      abre la ayuda con la lista entera, pendientes incluidos
 *   `G` `C`  va al catalogo
 *   `G` `P`  va a planes
 *   `Esc`    lo maneja Radix dentro del modal
 *
 * Agregar los que faltan es agregar una fila a `ATAJOS` el dia que su seccion
 * exista.
 *
 * LA MECANICA DE ACORDE `G` + TECLA
 * ──────────────────────────────────
 * Es la convencion de Gmail y GitHub: se aprieta `G`, se suelta, y la siguiente
 * tecla decide el destino. Hay una ventana de tiempo porque sin ella `G` se
 * quedaria armada para siempre y la proxima `C` que alguien escriba en cualquier
 * lado navegaria sola.
 */
'use client';

import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import { SECCIONES, destinoDelAcorde } from '@/lib/secciones';

import { Modal, Tabla } from './ui';

/** Cuanto espera el acorde a su segunda tecla. Mas que esto se siente pegajoso. */
const VENTANA_DEL_ACORDE_MS = 1500;

interface Atajo {
  teclas: string;
  descripcion: string;
  /** La seccion todavia no tiene pantalla: la ayuda lo dice, el acorde no va. */
  pendiente?: boolean;
}

/**
 * Los que no son de navegacion. Se declaran a mano porque no son secciones.
 *
 * `Esc` no esta cableado acá: lo maneja Radix adentro del modal. Figura en la
 * tabla porque la ayuda describe lo que el usuario puede hacer, no lo que este
 * archivo implementa.
 */
const ATAJOS_SUELTOS: readonly Atajo[] = [
  { teclas: '?', descripcion: 'Mostrar esta ayuda' },
  { teclas: 'Esc', descripcion: 'Cerrar el diálogo abierto' },
  { teclas: 'Ctrl+K', descripcion: 'Buscador global', pendiente: true },
  { teclas: 'Ctrl+N', descripcion: 'Crear nuevo', pendiente: true },
  { teclas: 'Ctrl+S', descripcion: 'Guardar', pendiente: true },
];

/**
 * La tabla de la ayuda, DERIVADA de las secciones.
 *
 * ⚠️ Esto es lo que arregla el desfasaje que habia acá. La version anterior
 * escribia la tabla a mano, con un campo `destino` que **nadie leia para
 * navegar** —navegaba un `switch` aparte—. La ayuda podia prometer un destino y
 * el acorde ir a otro lado, o a ninguno, sin que nada lo delatara.
 *
 * Ahora `pendiente` sale de `existe`, asi que la ayuda no puede anunciar como
 * disponible algo a donde `destinoDelAcorde` no lleva.
 */
function atajosDeNavegacion(): readonly Atajo[] {
  return SECCIONES.filter((seccion) => seccion.tecla).map((seccion) => ({
    teclas: `G luego ${seccion.tecla}`,
    descripcion: seccion.ayuda ?? `Ir a ${seccion.etiqueta}`,
    pendiente: !seccion.existe,
  }));
}

const ATAJOS: readonly Atajo[] = [
  ...ATAJOS_SUELTOS.filter((atajo) => !atajo.pendiente),
  ...atajosDeNavegacion(),
  ...ATAJOS_SUELTOS.filter((atajo) => atajo.pendiente),
];

/**
 * Un atajo no puede dispararse mientras alguien escribe.
 *
 * Sin esto, tipear "gc" en un campo de búsqueda te saca de la página. Se mira el
 * elemento con foco y no un estado propio, porque es la única fuente que no se
 * desincroniza.
 */
function escribiendo(destino: EventTarget | null): boolean {
  if (!(destino instanceof HTMLElement)) return false;
  if (destino.isContentEditable) return true;
  return ['INPUT', 'TEXTAREA', 'SELECT'].includes(destino.tagName);
}

export function AtajosDeTeclado() {
  const router = useRouter();
  const [ayudaAbierta, setAyudaAbierta] = useState(false);
  const [acordeArmado, setAcordeArmado] = useState(false);

  const alPresionar = useCallback(
    (evento: KeyboardEvent) => {
      if (escribiendo(evento.target)) return;
      // Un atajo con modificador es de otra combinación (Ctrl+K y compañía).
      if (evento.ctrlKey || evento.metaKey || evento.altKey) return;

      const tecla = evento.key.toLowerCase();

      if (acordeArmado) {
        setAcordeArmado(false);
        const destino = destinoDelAcorde(tecla);
        if (destino) {
          evento.preventDefault();
          router.push(destino);
        }
        return;
      }

      if (tecla === 'g') {
        setAcordeArmado(true);
        return;
      }

      if (evento.key === '?') {
        evento.preventDefault();
        setAyudaAbierta(true);
      }
    },
    [acordeArmado, router],
  );

  useEffect(() => {
    window.addEventListener('keydown', alPresionar);
    return () => window.removeEventListener('keydown', alPresionar);
  }, [alPresionar]);

  // La `G` se desarma sola. Sin esto queda armada indefinidamente y la próxima
  // `c` que alguien apriete —minutos después, en otra pantalla— navega sola.
  useEffect(() => {
    if (!acordeArmado) return;
    const reloj = window.setTimeout(() => setAcordeArmado(false), VENTANA_DEL_ACORDE_MS);
    return () => window.clearTimeout(reloj);
  }, [acordeArmado]);

  return (
    <Modal
      abierto={ayudaAbierta}
      alCerrar={() => setAyudaAbierta(false)}
      titulo="Atajos de teclado"
      descripcion="Los que están grises todavía no tienen sección a dónde ir."
    >
      <Tabla descripcion="Atajos de teclado disponibles" columnas={['Atajo', 'Qué hace']}>
        {ATAJOS.map((atajo) => (
          <tr key={atajo.teclas} className="border-b border-neutro-borde">
            <td className="py-1.5 pr-4 font-medium">
              <kbd>{atajo.teclas}</kbd>
            </td>
            <td className={`py-1.5 ${atajo.pendiente ? 'text-neutro-suave' : 'text-neutro-texto'}`}>
              {atajo.descripcion}
              {atajo.pendiente && ' (pendiente)'}
            </td>
          </tr>
        ))}
      </Tabla>
    </Modal>
  );
}
