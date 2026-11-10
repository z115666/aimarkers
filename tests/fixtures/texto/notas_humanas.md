# Notas migración MDM

Ayer movimos las tabletas del aula 2 al nuevo perfil. Fallaron 4, todas con la misma versión del sistema, así que tiene pinta de que es el perfil de Wi-Fi y no el MDM en sí.

Pendiente:
- revisar el perfil WPA2-Enterprise, el certificado caducaba el 12
- preguntar a compras por lo de las licencias
- pedir 2 cargadores más para el carro del segundo piso

Lo de los portátiles del laboratorio va más lento. El script de enrolamiento se cuelga si el equipo no tiene la hora bien, lo cual es absurdo pero pasa. Lo arreglé forzando la sincronización de hora antes de relanzar el perfil. Tardó un rato en salir porque el log no decía nada útil, solo un error 2 que no aparece documentado en ningún sitio. Si vuelve a pasar en los equipos de idiomas, lo primero es mirar la hora. Lo segundo, el certificado. No me fío nada del proxy esta semana, ha tenido dos caídas y nadie sabe por qué; el proveedor dice que es nuestro firewall y yo creo que es su actualización del viernes.

Para el lunes: pasar el inventario a la hoja nueva, avisar a secretaría del cambio de contraseñas y cerrar el ticket de la impresora de la sala de reuniones, que lleva abierto desde octubre y ya da vergüenza.
