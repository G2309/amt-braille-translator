// Descarga en el navegador mediante un Blob y un enlace temporal
import 'dart:js_interop';
import 'dart:typed_data';

import 'package:web/web.dart' as web;

Future<void> guardarArchivo(String nombre, List<int> bytes) async {
  final blob = web.Blob([Uint8List.fromList(bytes).toJS].toJS, web.BlobPropertyBag(type: 'application/octet-stream'));
  final url = web.URL.createObjectURL(blob);
  final enlace = web.HTMLAnchorElement()
    ..href = url
    ..download = nombre;
  web.document.body?.append(enlace);
  enlace.click();
  enlace.remove();
  web.URL.revokeObjectURL(url);
}
