/**
 * ⚠️ La unica seccion del menu sin change asignado, y es un dato, no un olvido.
 *
 * `knowledge-base/06` la tiene como epica E10 —reportes personalizables,
 * exportacion, canales de origen de leads—, pero todas esas HU son `Should` o
 * `Could` y caen en F4/F5. Ninguno de los 32 changes de `CHANGES.md` las toma:
 * el MVP termina en WhatsApp.
 *
 * Se pasa `null` en vez de inventarle un change. La pantalla lo dice, y quien
 * entre no va a salir a buscar un numero que no existe.
 */
import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Reportes',
};

export default function ReportesPage() {
  return (
    <SeccionEnConstruccion
      titulo="Reportes"
      descripcion="Exportaciones y reportes sobre la operación de la agencia. Está en la base de conocimiento como épica E10, pero es posterior al MVP: ningún change del roadmap la toma todavía."
      change={null}
    />
  );
}
