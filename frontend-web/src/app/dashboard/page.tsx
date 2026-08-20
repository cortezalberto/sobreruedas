import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Dashboard',
};

export default function DashboardPage() {
  return (
    <SeccionEnConstruccion
      titulo="Dashboard"
      descripcion="Los indicadores de la agencia: stock publicado, leads abiertos por etapa y actividad del equipo. Necesita que existan los datos que resume, así que llega después del CRM."
      change="C-28 crm-automatizaciones-y-dashboard"
    />
  );
}
