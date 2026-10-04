// Flujo principal: elegir la grabacion, ajustar parametros, convertir y descargar el BRF
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

import '../api.dart';
import '../braille.dart';
import '../descarga.dart';
import '../modo.dart';

const formatos = ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'opus', 'webm'];
const compases = [(2, 4), (3, 4), (4, 4), (2, 2), (3, 8), (6, 8)];

String nombreArmadura(int n) {
  const mayores = ['Do', 'Sol', 'Re', 'La', 'Mi', 'Si', 'Fa sostenido', 'Do sostenido'];
  const bemoles = ['Do', 'Fa', 'Si bemol', 'Mi bemol', 'La bemol', 'Re bemol', 'Sol bemol', 'Do bemol'];
  if (n == 0) return 'Sin alteraciones, Do mayor';
  final cuantos = n.abs();
  final tipo = n > 0 ? (cuantos == 1 ? 'sostenido' : 'sostenidos') : (cuantos == 1 ? 'bemol' : 'bemoles');
  return '$cuantos $tipo, ${n > 0 ? mayores[cuantos] : bemoles[cuantos]} mayor';
}

class Conversion extends StatefulWidget {
  const Conversion({super.key, required this.modo, required this.alCambiarModo, this.api, this.archivoInicial});
  final Modo modo;
  final VoidCallback alCambiarModo;
  final ApiCliente? api;
  // Grabacion ya elegida, para pruebas automaticas que no pueden abrir el selector de archivos
  final (String, Uint8List)? archivoInicial;

  @override
  State<Conversion> createState() => _ConversionState();
}

class _ConversionState extends State<Conversion> {
  late final ApiCliente _api = widget.api ?? ApiCliente();
  final _tempo = TextEditingController(text: '60');
  (int, int) _compas = (4, 4);
  int _armadura = 0;
  String? _nombre;
  Uint8List? _audio;
  String _estado = 'Todavía no ha elegido una grabación.';
  bool _ocupado = false;
  String? _brf;
  Timer? _consulta;

  @override
  void initState() {
    super.initState();
    final inicial = widget.archivoInicial;
    if (inicial != null) {
      _nombre = inicial.$1;
      _audio = inicial.$2;
      _estado = 'Grabación elegida: ${inicial.$1}.';
    }
  }

  @override
  void dispose() {
    _consulta?.cancel();
    _tempo.dispose();
    super.dispose();
  }

  Future<void> _elegir() async {
    final lista = await FilePicker.pickFiles(type: FileType.custom, allowedExtensions: formatos);
    if (lista.isEmpty) return;
    final archivo = lista.first;
    final bytes = await archivo.readAsBytes();
    setState(() {
      _audio = bytes;
      _nombre = archivo.name;
      _brf = null;
      _estado = 'Grabación elegida: ${archivo.name}, ${(bytes.length / 1048576).toStringAsFixed(1)} megabytes.';
    });
  }

  Future<void> _convertir() async {
    final tempo = double.tryParse(_tempo.text.replaceAll(',', '.'));
    if (tempo == null || tempo <= 0) {
      setState(() => _estado = 'El tempo debe ser un número mayor que cero.');
      return;
    }
    setState(() {
      _ocupado = true;
      _brf = null;
      _estado = 'Enviando la grabación al servidor.';
    });
    try {
      final id = await _api.enviar(_audio!, _nombre!, Parametros(tempo: tempo, beats: _compas.$1, beatType: _compas.$2, armadura: _armadura));
      setState(() => _estado = 'Grabación recibida. En espera de procesamiento.');
      _consulta = Timer.periodic(const Duration(seconds: 2), (_) => _revisar(id));
    } catch (e) {
      setState(() {
        _ocupado = false;
        _estado = 'No se pudo enviar la grabación. $e';
      });
    }
  }

  Future<void> _revisar(String id) async {
    try {
      final e = await _api.estado(id);
      if (!e.terminado) {
        final texto = e.estado == 'processing'
            ? 'Transcribiendo la grabación y traduciendo a Braille. Esto puede tardar unos minutos.'
            : 'En espera de procesamiento.';
        if (texto != _estado) setState(() => _estado = texto);
        return;
      }
      _consulta?.cancel();
      if (e.estado == 'error') {
        setState(() {
          _ocupado = false;
          _estado = 'La conversión falló. ${e.error}';
        });
        return;
      }
      final brf = await _api.brf(id);
      setState(() {
        _ocupado = false;
        _brf = brf;
        _estado = 'Listo. La partitura en Braille está disponible para descargar.';
      });
    } catch (e) {
      _consulta?.cancel();
      setState(() {
        _ocupado = false;
        _estado = 'Se perdió la conexión con el servidor. $e';
      });
    }
  }

  Future<void> _descargar() async {
    final nombre = '${(_nombre ?? 'partitura').replaceAll(RegExp(r'\.[^.]+$'), '')}.brf';
    await guardarArchivo(nombre, latin1.encode(_brf!));
    setState(() => _estado = 'Archivo $nombre guardado en descargas.');
  }

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final tutor = widget.modo == Modo.tutor;
    return Scaffold(
      appBar: AppBar(
        title: Semantics(header: true, child: const Text('Música en Braille', overflow: TextOverflow.ellipsis)),
      ),
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
                  // Fuera de la barra superior para que el texto pueda partirse en pantallas angostas
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: TextButton.icon(onPressed: widget.alCambiarModo, icon: const Icon(Icons.tune), label: Text('Modo ${widget.modo.nombre}. Cambiar modo')),
                  ),
                  const SizedBox(height: 16),
                  Semantics(header: true, child: Text('1. Grabación', style: texto.titleLarge)),
                  const SizedBox(height: 8),
                  Text('Formatos MP3, WAV, FLAC o la grabación del teléfono (M4A, AAC, OGG), de hasta cinco minutos.', style: texto.bodyMedium),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _ocupado ? null : _elegir,
                    icon: const Icon(Icons.audio_file),
                    label: Text(_nombre == null ? 'Elegir grabación' : 'Cambiar grabación'),
                  ),
                  const SizedBox(height: 24),
                  Semantics(header: true, child: Text('2. Datos de la obra', style: texto.titleLarge)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _tempo,
                    enabled: !_ocupado,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Tempo en negras por minuto',
                      helperText: 'Un valor aproximado basta; el sistema sigue el pulso de la grabación.',
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<(int, int)>(
                    initialValue: _compas,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Compás'),
                    items: [for (final c in compases) DropdownMenuItem(value: c, child: Text('${c.$1} por ${c.$2}'))],
                    onChanged: _ocupado ? null : (c) => setState(() => _compas = c!),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<int>(
                    initialValue: _armadura,
                    isExpanded: true,
                    decoration: const InputDecoration(labelText: 'Armadura'),
                    items: [for (var n = -7; n <= 7; n++) DropdownMenuItem(value: n, child: Text(nombreArmadura(n)))],
                    onChanged: _ocupado ? null : (n) => setState(() => _armadura = n!),
                  ),
                  const SizedBox(height: 24),
                  Semantics(header: true, child: Text('3. Conversión', style: texto.titleLarge)),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: _audio == null || _ocupado ? null : _convertir,
                    icon: const Icon(Icons.translate),
                    label: const Text('Convertir a Braille'),
                  ),
                  const SizedBox(height: 16),
                  Semantics(
                    liveRegion: true,
                    container: true,
                    label: 'Estado',
                    child: Text(_estado, style: texto.bodyLarge),
                  ),
                  if (_ocupado) ...[const SizedBox(height: 12), const LinearProgressIndicator(semanticsLabel: 'Conversión en curso')],
                  if (_brf != null) ...[
                    const SizedBox(height: 16),
                    FilledButton.icon(onPressed: _descargar, icon: const Icon(Icons.download), label: const Text('Descargar archivo BRF')),
                    if (tutor) ...[
                      const SizedBox(height: 24),
                      Semantics(header: true, child: Text('Vista previa en Braille', style: texto.titleLarge)),
                      const SizedBox(height: 8),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(border: Border.all(color: Theme.of(context).colorScheme.outline)),
                        child: SelectableText(brfAUnicode(_brf!), style: const TextStyle(fontSize: 20, height: 1.4)),
                      ),
                    ],
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
