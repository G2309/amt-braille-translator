// Guarda el BRF en el dispositivo; en web usa un enlace de descarga y fuera de web no hace nada
export 'descarga_stub.dart' if (dart.library.js_interop) 'descarga_web.dart';
