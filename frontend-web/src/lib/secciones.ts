/**
 * Catalogo de secciones del producto — C-07, `T-038`. Fuente unica.
 *
 * POR QUE ESTE ARCHIVO EXISTE
 * ────────────────────────────
 * "Que secciones hay" vivia repartido en TRES listas que nadie obligaba a
 * coincidir: la de la barra de navegacion, la tabla de la ayuda de `?`, y el
 * `switch` que el acorde `G` usaba para navegar de verdad.
 *
 * Las dos ultimas estaban en el mismo archivo y aun asi podian mentirse: la
 * tabla declaraba un `destino` que **nadie leia para navegar**. `G luego C`
 * podia decir "Ir al catálogo" en la ayuda y el `switch` mandar a otro lado
 * —o a ningun lado— sin que nada lo delatara.
 *
 * Ahora se declara una vez y todo lo demas se deriva. Agregar una seccion es
 * una linea acá, y la barra, la ayuda y el acorde se enteran juntos.
 *
 * DE DONDE SALE LA LISTA
 * ───────────────────────
 * `knowledge-base/15` §Navegacion del producto, que deriva del manual de
 * usuario. Las teclas de acorde son las de §230 (`G+D`, `G+S`, `G+L`, `G+M`,
 * `G+R`); Configuracion no tiene atajo en el documento y no se le inventa uno.
 *
 * `Inicio` tampoco esta en ese menu: es la portada, no una seccion del
 * producto. Se declara porque la barra la muestra.
 *
 * ⚠️ `existe` NO ES BUROCRACIA. Cinco de las seis secciones del menu no tienen
 * pantalla todavia. Declararlas apagadas es lo que permite que la ayuda las
 * liste como pendientes —que es informacion util— sin que la barra las muestre
 * ni el acorde lleve a un 404. Es el mismo criterio con el que este proyecto ya
 * se corrigio una vez: "un redirect a una ruta que no existe seria un 404
 * disfrazado de feature".
 *
 * El dia que la pantalla exista, se cambia `false` por `true` en un solo lugar.
 */

export interface Seccion {
  href: string;
  etiqueta: string;
  /** Segunda tecla del acorde `G`. En MAYUSCULA — ver `destinoDelAcorde`. */
  tecla?: string;
  /**
   * Como se lee el atajo en la ayuda de `?`.
   *
   * Se escribe a mano y no se arma con `Ir a ${etiqueta}` por el castellano:
   * daria "Ir a Stock" donde corresponde "Ir al stock". Que viva acá, al lado
   * del destino, es lo que impide que la frase y la ruta se contradigan — que
   * es justo el defecto que este archivo vino a cerrar.
   */
  ayuda?: string;
  /** `false` mientras la seccion no tenga pantalla. */
  existe: boolean;
}

export const SECCIONES: readonly Seccion[] = [
  { href: '/', etiqueta: 'Inicio', existe: true },
  { href: '/planes', etiqueta: 'Planes', tecla: 'P', ayuda: 'Ir a planes', existe: true },
  { href: '/catalogo', etiqueta: 'Catálogo', tecla: 'C', ayuda: 'Ir al catálogo', existe: true },
  {
    href: '/dashboard',
    etiqueta: 'Dashboard',
    tecla: 'D',
    ayuda: 'Ir al dashboard',
    existe: false,
  },
  { href: '/stock', etiqueta: 'Stock', tecla: 'S', ayuda: 'Ir al stock', existe: false },
  { href: '/leads', etiqueta: 'Leads', tecla: 'L', ayuda: 'Ir a leads', existe: false },
  { href: '/mensajes', etiqueta: 'Mensajes', tecla: 'M', ayuda: 'Ir a mensajes', existe: false },
  { href: '/reportes', etiqueta: 'Reportes', tecla: 'R', ayuda: 'Ir a reportes', existe: false },
  { href: '/configuracion', etiqueta: 'Configuración', existe: false },
] as const;

/**
 * Lo que la navegacion muestra: solo lo que tiene pantalla.
 *
 * Un item de menu que lleva a un 404 le enseña al usuario a desconfiar del
 * menu entero, y eso no se recupera agregando la pantalla despues.
 */
export function seccionesVisibles(): readonly Seccion[] {
  return SECCIONES.filter((seccion) => seccion.existe);
}

/**
 * A donde lleva `G` + `tecla`, si es que lleva a algun lado.
 *
 * Es un `find` sobre el array y NO un objeto indexado por la tecla. La clave
 * viene del teclado —entrada del usuario— y con un objeto plano apretar `G` y
 * despues `constructor` devolveria algo. `eslint-plugin-security` marca ese
 * acceso por indice, y acá la advertencia ni siquiera es un falso positivo.
 *
 * @param tecla en minuscula, tal como llega de `evento.key.toLowerCase()`.
 */
export function destinoDelAcorde(tecla: string): string | undefined {
  const seccion = SECCIONES.find(
    (candidata) => candidata.existe && candidata.tecla?.toLowerCase() === tecla,
  );
  return seccion?.href;
}
