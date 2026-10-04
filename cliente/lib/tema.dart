// Temas de cada modo; los pares de color se eligieron para superar WCAG AA en el tutor y AAA en los otros dos
import 'package:flutter/material.dart';

import 'modo.dart';

const tutorFondo = Color(0xFFFFFFFF);
const tutorTexto = Color(0xFF1A1A1A);
const tutorSecundario = Color(0xFF4A4A4A);
const tutorPrimario = Color(0xFF1C5CAB);
const altoFondo = Color(0xFF000000);
const altoTexto = Color(0xFFFFFFFF);
const altoPrimario = Color(0xFFFFD400);

// Factor minimo de texto y alto minimo de los controles por modo
double escalaMinima(Modo modo) => modo == Modo.bajaVision ? 1.6 : 1.0;
double altoControl(Modo modo) => modo == Modo.tutor ? 48 : 64;

ThemeData temaPara(Modo modo) {
  final alto = modo != Modo.tutor;
  final fondo = alto ? altoFondo : tutorFondo;
  final texto = alto ? altoTexto : tutorTexto;
  final primario = alto ? altoPrimario : tutorPrimario;
  final sobrePrimario = alto ? altoFondo : tutorFondo;
  final esquema = ColorScheme(
    brightness: alto ? Brightness.dark : Brightness.light,
    primary: primario,
    onPrimary: sobrePrimario,
    secondary: primario,
    onSecondary: sobrePrimario,
    error: alto ? const Color(0xFFFF9E9E) : const Color(0xFFB3261E),
    onError: alto ? altoFondo : tutorFondo,
    surface: fondo,
    onSurface: texto,
    onSurfaceVariant: alto ? altoTexto : tutorSecundario,
    outline: alto ? altoTexto : tutorSecundario,
  );
  final borde = BorderSide(color: alto ? altoTexto : tutorSecundario, width: alto ? 3 : 1);
  final foco = BorderSide(color: primario, width: alto ? 4 : 2);
  final minimo = Size(altoControl(modo), altoControl(modo));
  return ThemeData(
    colorScheme: esquema,
    scaffoldBackgroundColor: fondo,
    useMaterial3: true,
    visualDensity: VisualDensity.standard,
    materialTapTargetSize: MaterialTapTargetSize.padded,
    focusColor: primario.withValues(alpha: 0.35),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: minimo, textStyle: const TextStyle(fontWeight: FontWeight.w600)),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(minimumSize: minimo, foregroundColor: texto, side: borde),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderSide: borde),
      enabledBorder: OutlineInputBorder(borderSide: borde),
      focusedBorder: OutlineInputBorder(borderSide: foco),
      labelStyle: TextStyle(color: texto),
    ),
  );
}
