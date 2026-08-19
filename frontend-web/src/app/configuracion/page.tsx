import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Configuración',
};

export default function ConfiguracionPage() {
  return (
    <SeccionEnConstruccion
      titulo="Configuración"
      descripcion="Los datos de la agencia, su gente y sus sucursales: invitar usuarios, asignar roles y ajustar las preferencias del tenant. No tiene atajo de teclado — el menú de la KB no le asigna ninguno y no se le inventa."
      change="C-12 usuarios-invitaciones-y-settings"
    />
  );
}
