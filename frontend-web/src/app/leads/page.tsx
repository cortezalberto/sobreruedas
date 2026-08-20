import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Leads',
};

export default function LeadsPage() {
  return (
    <SeccionEnConstruccion
      titulo="Leads"
      descripcion="Las consultas que entran, en un tablero por etapa del pipeline. Cada tarjeta es una persona interesada, con su historial y la próxima acción a hacer."
      change="C-27 crm-web-kanban-y-leads"
    />
  );
}
