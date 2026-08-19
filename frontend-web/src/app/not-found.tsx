/**
 * Pagina de no encontrado.
 *
 * Existe porque la de Next viene en ingles —"This page could not be found"— y el
 * documento declara `lang="es-AR"`. Un lector de pantalla la pronuncia con voz
 * castellana y no se entiende nada; y para el que lee, cambiar de idioma justo
 * en el error es la clase de detalle que hace parecer que la aplicacion se
 * rompio mas de lo que se rompio.
 *
 * La usa `notFound()` desde cualquier ruta. Hoy la llama `/catalogo/[marca]`
 * cuando el backend devuelve 404, que es una marca inexistente y no una falla.
 */
import Link from 'next/link';

export const metadata = {
  title: 'No encontrado',
};

export default function NoEncontrado() {
  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-3xl font-semibold tracking-tight">No encontrado</h1>
      <p className="mt-2 text-neutro-texto">
        La pagina que buscas no existe. Puede que el enlace este mal escrito o que el contenido ya
        no este publicado.
      </p>

      <Link href="/" className="mt-6 inline-block text-sm underline underline-offset-4">
        Volver al inicio
      </Link>
    </div>
  );
}
