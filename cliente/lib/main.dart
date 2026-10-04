// Cliente accesible del sistema de musicografia Braille, publicado como PWA
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import 'api.dart';
import 'modo.dart';
import 'pantallas/conversion.dart';
import 'pantallas/seleccion_modo.dart';
import 'tema.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Activa el arbol de semantica desde el inicio para que el lector de pantalla no dependa de un boton oculto
  SemanticsBinding.instance.ensureSemantics();
  final controlador = ControladorModo();
  await controlador.cargar();
  runApp(AplicacionBraille(controlador: controlador));
}

class AplicacionBraille extends StatelessWidget {
  const AplicacionBraille({super.key, required this.controlador, this.api, this.archivoInicial});
  final ControladorModo controlador;
  final ApiCliente? api;
  final (String, Uint8List)? archivoInicial;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controlador,
      builder: (context, _) {
        final elegido = controlador.modo;
        final modo = elegido ?? sugerirModo(MediaQueryData.fromView(View.of(context)));
        return MaterialApp(
          title: 'Música en Braille',
          debugShowCheckedModeBanner: false,
          theme: temaPara(modo),
          builder: (context, hijo) {
            final datos = MediaQuery.of(context);
            final escala = datos.textScaler.scale(1.0).clamp(escalaMinima(modo), 3.0);
            return MediaQuery(data: datos.copyWith(textScaler: TextScaler.linear(escala)), child: hijo!);
          },
          home: elegido == null
              ? SeleccionModo(controlador: controlador)
              : Conversion(modo: elegido, alCambiarModo: () => _elegirOtro(context), api: api, archivoInicial: archivoInicial),
        );
      },
    );
  }

  void _elegirOtro(BuildContext context) => controlador.limpiar();
}
