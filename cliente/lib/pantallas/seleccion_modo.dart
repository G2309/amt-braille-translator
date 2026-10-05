// Primera pantalla: elegir el modo de la interfaz, con el sugerido por los ajustes del sistema primero
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import '../modo.dart';

class SeleccionModo extends StatelessWidget {
  const SeleccionModo({super.key, required this.controlador});
  final ControladorModo controlador;

  @override
  Widget build(BuildContext context) {
    final sugerido = sugerirModo(MediaQuery.of(context));
    final orden = [sugerido, ...Modo.values.where((m) => m != sugerido)];
    final texto = Theme.of(context).textTheme;
    return Scaffold(
      // Region principal, separada de la barra superior, para saltar directo al contenido
      body: Semantics(
        role: SemanticsRole.main,
        container: true,
        explicitChildNodes: true,
        child: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Semantics(header: true, child: Text('Música en Braille', style: texto.headlineMedium)),
                  const SizedBox(height: 8),
                  Text('Elija cómo quiere usar la aplicación. Puede cambiarlo después.', style: texto.bodyLarge),
                  const SizedBox(height: 24),
                  for (final modo in orden) ...[
                    _OpcionModo(modo: modo, sugerido: modo == sugerido, alElegir: () => controlador.elegir(modo)),
                    const SizedBox(height: 16),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _OpcionModo extends StatelessWidget {
  const _OpcionModo({required this.modo, required this.sugerido, required this.alElegir});
  final Modo modo;
  final bool sugerido;
  final VoidCallback alElegir;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final titulo = sugerido ? '${modo.nombre} (sugerido)' : modo.nombre;
    return Semantics(
      button: true,
      label: 'Usar modo $titulo. ${modo.descripcion}',
      excludeSemantics: true,
      onTap: alElegir,
      child: OutlinedButton(
        onPressed: alElegir,
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.all(16),
          alignment: Alignment.centerLeft,
          // Rectángulo redondeado: la píldora por omisión recorta el texto de varias líneas
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(titulo, style: texto.titleLarge),
            const SizedBox(height: 4),
            Text(modo.descripcion, style: texto.bodyMedium),
          ],
        ),
      ),
    );
  }
}
