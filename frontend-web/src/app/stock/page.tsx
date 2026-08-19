import { SeccionEnConstruccion } from '@/components/SeccionEnConstruccion';

export const metadata = {
  title: 'Stock',
};

export default function StockPage() {
  return (
    <SeccionEnConstruccion
      titulo="Stock"
      descripcion="Los vehículos de la agencia: listado con filtros, ficha de cada unidad y su estado de publicación. Es la pantalla que reemplaza a la planilla."
      change="C-19 stock-web-listado-y-detalle"
    />
  );
}
