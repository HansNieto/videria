# Tipografías

Las tres que piden los estilos de subtítulo por defecto. Viajan con la
herramienta porque, si no, en una instalación nueva los subtítulos se quedan
sin fuente: el código las buscaba en `~/MoneyPrinterTurbo/resource/fonts`, que
solo existe si tenés ese proyecto instalado.

| Archivo | Familia | Se usa en | Origen |
|---|---|---|---|
| `Inter-Black.ttf` | Inter Black | estilo `capcut` (el de por defecto) | https://rsms.me/inter/ |
| `Anton-Regular.ttf` | Anton | estilo `titular` | https://fonts.google.com/specimen/Anton |
| `BebasNeue-Regular.ttf` | Bebas Neue | estilo `bloque` | https://fonts.google.com/specimen/Bebas+Neue |

Las tres están bajo la **SIL Open Font License 1.1**, que permite usarlas,
modificarlas y redistribuirlas —también dentro de un proyecto comercial— con
dos condiciones: que la licencia viaje con ellas (este archivo) y que no se
vendan por sí solas. El texto completo está en
https://openfontlicense.org y también dentro de cada `.ttf`, en el campo
`License Description` de su tabla `name`.

Para usar otra: dejala en `<proyecto>/fonts/`, o apuntá `VCUT_FONTS` a tu
carpeta. Las dos se miran antes que estas.
