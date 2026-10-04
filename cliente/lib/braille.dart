// Conversion de Braille ASCII (BRF) a celdas Unicode para la vista previa
const _ascii = " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[\$+X!&;:4\\0Z7(_?W]#Y)=";

String brfAUnicode(String brf) {
  final salida = StringBuffer();
  for (final caracter in brf.split('')) {
    if (caracter == '\n' || caracter == '\r' || caracter == '\f') {
      if (caracter == '\n') salida.write('\n');
      continue;
    }
    final indice = _ascii.indexOf(caracter.toUpperCase());
    salida.writeCharCode(0x2800 + (indice < 0 ? 0 : indice));
  }
  return salida.toString();
}
