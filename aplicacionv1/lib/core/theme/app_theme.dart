import 'package:flutter/material.dart';

abstract final class ExbColors {
  static const background = Color(0xFFF5F7F1);
  static const paper = Color(0xFFFFFFFF);
  static const green = Color(0xFF245741);
  static const dark = Color(0xFF203E31);
  static const muted = Color(0xFF768577);
  static const secondaryText = Color(0xFF566958);
  static const lime = Color(0xFFD9EDAA);
  static const line = Color(0xFFE0E7DA);
  static const amber = Color(0xFF9B6A24);
  static const story = Color(0xFFE4ECD6);
  static const books = Color(0xFFB4D38C);
  static const execution = Color(0xFF177C56);
}

ThemeData appTheme() {
  final scheme =
      ColorScheme.fromSeed(
        seedColor: ExbColors.green,
        surface: ExbColors.paper,
      ).copyWith(
        primary: ExbColors.green,
        onPrimary: Colors.white,
        secondary: ExbColors.lime,
        onSecondary: ExbColors.dark,
        outlineVariant: ExbColors.line,
      );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: ExbColors.background,
    fontFamily: 'Arial',
    textTheme: ThemeData.light().textTheme.apply(
      bodyColor: ExbColors.dark,
      displayColor: ExbColors.dark,
    ),
    dividerColor: ExbColors.line,
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: ExbColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: const BorderSide(color: ExbColors.line),
      ),
      labelStyle: const TextStyle(color: ExbColors.secondaryText, fontSize: 13),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size(44, 48),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(44, 44),
        side: const BorderSide(color: ExbColors.line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: ExbColors.story,
      side: BorderSide.none,
      labelStyle: const TextStyle(color: ExbColors.green, fontSize: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
    tooltipTheme: const TooltipThemeData(
      waitDuration: Duration(milliseconds: 400),
    ),
  );
}
