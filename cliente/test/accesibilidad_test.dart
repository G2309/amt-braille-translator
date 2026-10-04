// Evaluacion automatica de accesibilidad: guias de Flutter, arbol de semantica, teclado y reflujo por modo, pantalla y tamaño
import 'dart:convert';
import 'dart:io';

import 'package:amt_braille/api.dart';
import 'package:amt_braille/main.dart';
import 'package:amt_braille/modo.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

const anchos = [Size(320, 640), Size(768, 1024), Size(1280, 800)];
const escalas = [1.0, 2.0];
final guias = <String, AccessibilityGuideline>{
  'objetivo_android_48dp': androidTapTargetGuideline,
  'objetivo_ios_44pt': iOSTapTargetGuideline,
  'objetivos_etiquetados': labeledTapTargetGuideline,
  'contraste_texto_wcag': textContrastGuideline,
};
final filas = <Map<String, Object?>>[];

// API simulada que termina el trabajo en la primera consulta
ApiCliente apiSimulada() => ApiCliente(
      base: 'http://prueba',
      cliente: MockClient((r) async {
        if (r.method == 'POST') return http.Response('{"id": "t1", "status": "queued"}', 202);
        if (r.url.path.endsWith('/brf')) return http.Response.bytes(latin1.encode('#c4\n.> m vm.&\n_> m m\n'), 200);
        return http.Response('{"id": "t1", "status": "done"}', 200);
      }),
    );

// Recorre el arbol de semantica y cuenta los nodos interactivos con y sin etiqueta
(int, int, List<String>) auditarSemantica() {
  final raiz = RendererBinding.instance.renderViews.first.owner!.semanticsOwner!.rootSemanticsNode!;
  var interactivos = 0, etiquetados = 0;
  final sinEtiqueta = <String>[];
  void visitar(SemanticsNode n) {
    final d = n.getSemanticsData();
    final interactivo = d.hasAction(SemanticsAction.tap) || d.flagsCollection.isTextField;
    if (interactivo) {
      interactivos++;
      if (d.label.trim().isNotEmpty || d.value.trim().isNotEmpty || d.hint.trim().isNotEmpty) {
        etiquetados++;
      } else {
        sinEtiqueta.add(d.toString());
      }
    }
    n.visitChildren((h) {
      visitar(h);
      return true;
    });
  }
  visitar(raiz);
  return (interactivos, etiquetados, sinEtiqueta);
}

// Pulsa Tab hasta dar la vuelta y cuenta cuantos controles distintos reciben el foco
Future<int> recorrerConTeclado(WidgetTester tester) async {
  final vistos = <FocusNode>{};
  for (var i = 0; i < 40; i++) {
    await tester.sendKeyEvent(LogicalKeyboardKey.tab);
    await tester.pump();
    final foco = FocusManager.instance.primaryFocus;
    if (foco == null) continue;
    if (!vistos.add(foco)) break;
  }
  return vistos.length;
}

Future<void> evaluar(WidgetTester tester, {required String pantalla, Modo? modo, bool conResultado = false}) async {
  for (final tam in anchos) {
    for (final escala in escalas) {
      SharedPreferences.setMockInitialValues({});
      tester.view.physicalSize = tam;
      tester.view.devicePixelRatio = 1.0;
      tester.platformDispatcher.textScaleFactorTestValue = escala;
      final handle = tester.ensureSemantics();
      final controlador = ControladorModo();
      if (modo != null) await controlador.elegir(modo);
      await tester.pumpWidget(AplicacionBraille(
        controlador: controlador,
        api: apiSimulada(),
        archivoInicial: modo == null ? null : ('prueba.m4a', Uint8List(16)),
      ));
      await tester.pumpAndSettle();
      if (conResultado) {
        await tester.scrollUntilVisible(find.text('Convertir a Braille'), 200, scrollable: find.descendant(of: find.byType(ListView), matching: find.byType(Scrollable)).first);
        await tester.pumpAndSettle();
        await tester.tap(find.text('Convertir a Braille'));
        await tester.pump();
        await tester.pump(const Duration(seconds: 3));
        await tester.pump(const Duration(milliseconds: 200));
      }
      final fila = <String, Object?>{'pantalla': pantalla, 'modo': modo?.name ?? 'sin_elegir', 'ancho': tam.width, 'escala_texto': escala};
      for (final g in guias.entries) {
        final r = await g.value.evaluate(tester);
        fila[g.key] = r.passed;
        if (!r.passed) fila['${g.key}_detalle'] = r.reason;
      }
      final excepcion = tester.takeException();
      fila['sin_desbordes'] = excepcion == null;
      if (excepcion != null) fila['desborde_detalle'] = excepcion.toString().split('\n').first;
      final (total, etiquetados, faltan) = auditarSemantica();
      fila['interactivos'] = total;
      fila['interactivos_etiquetados'] = etiquetados;
      if (faltan.isNotEmpty) fila['sin_etiqueta'] = faltan;
      fila['alcanzables_con_teclado'] = await recorrerConTeclado(tester);
      filas.add(fila);
      handle.dispose();
      await tester.pumpWidget(const SizedBox());
      tester.view.reset();
      tester.platformDispatcher.clearTextScaleFactorTestValue();
    }
  }
}

void main() {
  testWidgets('seleccion de modo', (t) => evaluar(t, pantalla: 'seleccion_modo'));
  for (final modo in Modo.values) {
    testWidgets('conversion inicial ${modo.name}', (t) => evaluar(t, pantalla: 'conversion_inicial', modo: modo));
    testWidgets('conversion con resultado ${modo.name}', (t) => evaluar(t, pantalla: 'conversion_resultado', modo: modo, conResultado: true));
  }
  tearDownAll(() {
    final salida = File('../results/cliente_accesibilidad.json');
    salida.writeAsStringSync(const JsonEncoder.withIndent('  ').convert(filas));
  });
}
