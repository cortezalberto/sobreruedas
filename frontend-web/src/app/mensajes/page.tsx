import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Mensajes',
};

export default function MensajesPage() {
  return (
    <SeccionEnConstruccion
      titulo="Mensajes"
      descripcion="La bandeja de WhatsApp de la agencia: conversaciones con cada contacto y las plantillas aprobadas por Meta. Es la última cadena del MVP y es estrictamente secuencial."
      change="C-31 whatsapp-web-inbox-y-templates"
    />
  );
}
