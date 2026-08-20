## Purpose

Establece cómo el sistema decide si el sujeto de una petición puede hacer lo que pide, garantizando que esa decisión se tome siempre del lado del servidor y que negar el acceso sea el resultado por defecto ante cualquier duda.

## ADDED Requirements

### Requirement: La autorización se decide en el backend

El sistema SHALL verificar la autorización de toda petición en el backend, con independencia de lo que el cliente muestre u oculte.

Que una interfaz no ofrezca una acción MUST NOT considerarse un control de acceso. Un cliente que invoque directamente una operación para la que no está autorizado MUST recibir un rechazo por falta de permisos.

#### Scenario: Operación invocada sin pasar por la interfaz

- **WHEN** un sujeto invoca directamente una operación que su interfaz no le ofrece y para la que no está autorizado
- **THEN** la petición es rechazada por falta de permisos

#### Scenario: Autenticado no es autorizado

- **WHEN** un sujeto correctamente autenticado pide una operación fuera de su alcance
- **THEN** la petición es rechazada por falta de permisos
- **AND** el rechazo se distingue del de falta de autenticación

### Requirement: Denegar por defecto

Toda operación SHALL declarar explícitamente quién puede ejecutarla.

Una operación sin declaración de acceso MUST comportarse como denegada para todos, nunca como abierta. La verificación MUST ser detectable por inspección automática, de modo que una operación sin declarar pueda encontrarse antes de publicarse.

#### Scenario: Operación sin declaración de acceso

- **WHEN** una operación no declara quién puede ejecutarla
- **THEN** ninguna petición a esa operación es autorizada

#### Scenario: Inventario de operaciones sin declarar

- **WHEN** se inspecciona el conjunto de operaciones expuestas
- **THEN** puede obtenerse la lista de las que no declaran acceso

### Requirement: Verificación por rol y por permiso fino

El sistema SHALL ofrecer dos niveles de verificación: por **rol**, y por **permiso** cuando el rol no alcance para expresar la regla.

El nivel fino MUST poder expresar que el acceso de un sujeto a un recurso quede acotado a un subconjunto de sus campos —**tanto para modificarlos como para verlos**— y que su alcance quede acotado a los recursos que tiene asignados.

#### Scenario: Rol suficiente

- **WHEN** un sujeto cuyo rol está autorizado ejecuta la operación
- **THEN** la operación se ejecuta

#### Scenario: Rol insuficiente

- **WHEN** un sujeto cuyo rol no está autorizado ejecuta la operación
- **THEN** la petición es rechazada por falta de permisos

#### Scenario: Modificación acotada a ciertos campos

- **WHEN** un sujeto autorizado a modificar solo ciertos campos intenta modificar otro
- **THEN** la petición es rechazada por falta de permisos
- **AND** ningún campo del recurso queda modificado

#### Scenario: Lectura acotada a ciertos campos

- **WHEN** un sujeto autorizado a leer un recurso, pero no todos sus campos, lo consulta
- **THEN** la respuesta no incluye los campos excluidos
- **AND** el resto del recurso se devuelve normalmente

#### Scenario: Campo excluido pedido explícitamente

- **WHEN** ese mismo sujeto pide el recurso filtrando, ordenando o proyectando por un campo que no puede ver
- **THEN** el valor del campo no se revela por ningún medio

#### Scenario: Alcance acotado al propio sujeto

- **WHEN** un sujeto opera sobre un recurso que **es** él mismo —su sesión, su perfil— y su alcance es el propio sujeto
- **THEN** la operación se ejecuta
- **AND** la misma operación sobre otro sujeto es rechazada por falta de permisos

#### Scenario: Alcance acotado a lo asignado

- **WHEN** un sujeto cuyo alcance son los recursos que tiene asignados pide uno que no lo está
- **THEN** la petición es rechazada por falta de permisos

#### Scenario: El alcance sigue a la asignación vigente

- **WHEN** un recurso deja de estar asignado a un sujeto cuyo alcance son los recursos asignados
- **THEN** ese sujeto deja de acceder al recurso
- **AND** haberlo creado no le conserva el acceso

### Requirement: El alcance fino llega al cambio de estado

Cuando una operación cambie el estado de un recurso, el sistema SHALL poder acotar **qué cambios de estado** alcanza cada rol, dentro de los que las reglas de negocio consideran válidos.

Las reglas de estado del dominio acotan qué transiciones existen, no quién las hace. Sin este nivel, un sujeto MAY alcanzar un estado que no le corresponde **encadenando transiciones que sí le corresponden**, sin encontrar ningún control en el medio.

El rechazo por transición no autorizada MUST distinguirse del rechazo por transición inválida: el primero se resuelve pidiéndoselo a otro rol, el segundo no se resuelve.

#### Scenario: Transición autorizada

- **WHEN** un sujeto pide un cambio de estado que su rol tiene declarado
- **THEN** el cambio se aplica

#### Scenario: Transición válida que el rol no alcanza

- **WHEN** un sujeto pide un cambio de estado que las reglas de negocio admiten pero su rol no tiene declarado
- **THEN** la petición es rechazada por falta de permisos
- **AND** el rechazo se distingue del de transición inválida
- **AND** el estado del recurso no cambia

#### Scenario: Estado alcanzado encadenando transiciones

- **WHEN** un sujeto encadena dos cambios de estado para llegar a uno que su rol no tiene declarado
- **THEN** el segundo cambio es rechazado por falta de permisos

### Requirement: Los roles no acumulan permisos entre sí

El sistema SHALL definir los permisos de cada rol de forma independiente, **sin herencia ni contención** entre roles.

Conceder un permiso a un rol MUST NOT concederlo a ningún otro. Ningún rol puede definirse como extensión de otro, y la verificación de cobertura MUST recorrer cada rol por separado en lugar de asumir que uno contiene a otro.

#### Scenario: Permiso concedido a un solo rol

- **WHEN** se concede un permiso a un rol
- **THEN** ningún otro rol queda autorizado para esa operación

#### Scenario: Verificación sin asumir contención

- **WHEN** se verifica la cobertura de autorización
- **THEN** cada rol se evalúa contra cada operación por separado

### Requirement: El catálogo de roles es único y consultable

El sistema SHALL definir el catálogo de roles en un único lugar, consultable por el resto del sistema.

Ninguna operación puede declarar un rol que el catálogo no contenga. Declarar un rol inexistente MUST fallar de forma detectable y no MUST interpretarse como "nadie" ni como "cualquiera".

#### Scenario: Rol declarado fuera del catálogo

- **WHEN** una operación declara un rol que el catálogo no contiene
- **THEN** el error es detectable antes de atender peticiones

#### Scenario: Fuente única

- **WHEN** se consulta el catálogo de roles desde cualquier parte del sistema
- **THEN** se obtiene la misma definición

### Requirement: La operación cross-tenant está separada

El sistema SHALL reservar el acceso a datos de más de un tenant a un rol de plataforma, y **exclusivamente** bajo el espacio de rutas administrativo.

Ningún rol de tenant puede acceder a datos de otro tenant por ninguna ruta. El rol de plataforma MUST NOT obtener acceso cross-tenant fuera de ese espacio de rutas.

#### Scenario: Rol de tenant pide datos de otro tenant

- **WHEN** un sujeto con rol de tenant pide datos de un tenant distinto al suyo
- **THEN** la petición es rechazada
- **AND** no se devuelven datos del otro tenant

#### Scenario: Rol de plataforma en el espacio administrativo

- **WHEN** el rol de plataforma opera bajo el espacio de rutas administrativo
- **THEN** puede acceder a datos de más de un tenant

#### Scenario: Rol de plataforma fuera del espacio administrativo

- **WHEN** el rol de plataforma opera fuera del espacio de rutas administrativo
- **THEN** no obtiene acceso cross-tenant

#### Scenario: Rol de tenant en el espacio administrativo

- **WHEN** un sujeto con rol de tenant accede al espacio de rutas administrativo
- **THEN** la petición es rechazada por falta de permisos

### Requirement: Cobertura verificable de la autorización

El sistema SHALL permitir verificar automáticamente el resultado de autorización de **cada operación expuesta frente a cada rol del catálogo**.

La verificación MUST recorrer las operaciones realmente expuestas y no una lista mantenida a mano, y MUST distinguir el permitido del rechazo por falta de permisos, de modo que un cambio que abra una operación de más se detecte.

#### Scenario: Operación que se abre de más

- **WHEN** una operación pasa a autorizar un rol que antes rechazaba
- **THEN** la verificación lo reporta

#### Scenario: Operación nueva sin cobertura

- **WHEN** se expone una operación nueva
- **THEN** la verificación la incluye sin que haya que agregarla a una lista
