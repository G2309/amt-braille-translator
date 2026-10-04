// Cliente de la API REST del sistema
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

const urlApi = String.fromEnvironment('API_URL', defaultValue: 'http://localhost:8000');

class Parametros {
  const Parametros({this.tempo = 60, this.beats = 4, this.beatType = 4, this.armadura = 0});
  final double tempo;
  final int beats;
  final int beatType;
  final int armadura;
}

class EstadoTrabajo {
  EstadoTrabajo(this.json);
  final Map<String, dynamic> json;
  String get estado => json['status'] as String? ?? 'queued';
  String get error => json['error'] as String? ?? '';
  bool get terminado => estado == 'done' || estado == 'error';
}

class ApiCliente {
  ApiCliente({String? base, http.Client? cliente})
      : base = base ?? urlApi,
        _http = cliente ?? http.Client();
  final String base;
  final http.Client _http;

  Future<String> enviar(Uint8List audio, String nombre, Parametros p) async {
    final peticion = http.MultipartRequest('POST', Uri.parse('$base/transcriptions'))
      ..files.add(http.MultipartFile.fromBytes('file', audio, filename: nombre))
      ..fields.addAll({
        'tempo_bpm': '${p.tempo}',
        'beats': '${p.beats}',
        'beat_type': '${p.beatType}',
        'fifths': '${p.armadura}',
      });
    final respuesta = await http.Response.fromStream(await _http.send(peticion));
    if (respuesta.statusCode != 202) {
      throw ErrorApi(_detalle(respuesta));
    }
    return (jsonDecode(respuesta.body) as Map<String, dynamic>)['id'] as String;
  }

  Future<EstadoTrabajo> estado(String id) async {
    final r = await _http.get(Uri.parse('$base/transcriptions/$id'));
    if (r.statusCode != 200) throw ErrorApi(_detalle(r));
    return EstadoTrabajo(jsonDecode(r.body) as Map<String, dynamic>);
  }

  Future<String> brf(String id) async {
    final r = await _http.get(Uri.parse('$base/transcriptions/$id/brf'));
    if (r.statusCode != 200) throw ErrorApi(_detalle(r));
    return latin1.decode(r.bodyBytes);
  }

  String _detalle(http.Response r) {
    try {
      return (jsonDecode(r.body) as Map<String, dynamic>)['detail'].toString();
    } catch (_) {
      return 'El servidor respondió con el código ${r.statusCode}.';
    }
  }
}

class ErrorApi implements Exception {
  ErrorApi(this.mensaje);
  final String mensaje;
  @override
  String toString() => mensaje;
}
