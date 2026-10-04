// Modos de la interfaz y su preferencia guardada en el dispositivo
import 'package:flutter/widgets.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum Modo { tutor, bajaVision, nulaVision }

extension ModoTexto on Modo {
  String get nombre => switch (this) {
        Modo.tutor => 'Tutor',
        Modo.bajaVision => 'Baja visión',
        Modo.nulaVision => 'Lector de pantalla',
      };

  String get descripcion => switch (this) {
        Modo.tutor => 'Interfaz estándar con todos los parámetros y la vista previa del Braille, para docentes y personas videntes.',
        Modo.bajaVision => 'Alto contraste, texto grande y botones amplios para personas con visibilidad reducida.',
        Modo.nulaVision => 'Flujo lineal pensado para TalkBack, VoiceOver, NVDA y otros lectores de pantalla.',
      };
}

// Sugiere un modo a partir de los ajustes de accesibilidad del sistema
Modo sugerirModo(MediaQueryData datos) {
  if (datos.accessibleNavigation) return Modo.nulaVision;
  if (datos.highContrast || datos.textScaler.scale(1.0) >= 1.3) return Modo.bajaVision;
  return Modo.tutor;
}

class ControladorModo extends ChangeNotifier {
  static const _clave = 'modo';
  Modo? _modo;

  Modo? get modo => _modo;

  Future<void> cargar() async {
    final prefs = await SharedPreferences.getInstance();
    final guardado = prefs.getString(_clave);
    _modo = Modo.values.where((m) => m.name == guardado).firstOrNull;
    notifyListeners();
  }

  // Vuelve a la pantalla de seleccion de modo
  Future<void> limpiar() async {
    _modo = null;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_clave);
  }

  Future<void> elegir(Modo modo) async {
    _modo = modo;
    notifyListeners();
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_clave, modo.name);
  }
}
