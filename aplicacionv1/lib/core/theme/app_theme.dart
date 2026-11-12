import 'package:flutter/material.dart';

/// Institutional palette. [night] is set by ExbApp before each build; the whole
/// route tree is remounted on change, so every widget reads the new tokens.
abstract final class ExbColors {
  static bool night = false;
  static Color _pick(int day, int dark) => Color(night ? dark : day);

  static Color get background => _pick(0xFFF5F7F1, 0xFF0D1511);
  static Color get paper => _pick(0xFFFFFFFF, 0xFF15201A);
  static Color get green => _pick(0xFF245741, 0xFF7CCB97);
  static Color get dark => _pick(0xFF203E31, 0xFFE4EEE6);
  static Color get muted => _pick(0xFF768577, 0xFF8EA394);
  static Color get secondaryText => _pick(0xFF566958, 0xFFA8BAAC);
  static Color get lime => _pick(0xFFD9EDAA, 0xFF2D4A2E);
  static Color get line => _pick(0xFFE0E7DA, 0xFF26352D);
  static Color get amber => _pick(0xFF9B6A24, 0xFFE3AE63);
  static Color get story => _pick(0xFFE4ECD6, 0xFF1D2C23);
  static Color get books => _pick(0xFFB4D38C, 0xFF7FA968);
  static Color get execution => _pick(0xFF177C56, 0xFF43B883);

  /// Filled surfaces such as the user's chat bubble and primary buttons.
  static Color get primaryFill => _pick(0xFF245741, 0xFF3E8E62);
  static Color get onPrimaryFill => const Color(0xFFFFFFFF);

  /// Bright glow from Juku's illustrations, behind poses in night mode.
  static const glow = Color(0xFF9BD13B);
}

ThemeData appTheme({required bool dark}) {
  ExbColors.night = dark;
  final scheme =
      ColorScheme.fromSeed(
        seedColor: const Color(0xFF245741),
        brightness: dark ? Brightness.dark : Brightness.light,
        surface: ExbColors.paper,
      ).copyWith(
        primary: ExbColors.primaryFill,
        onPrimary: ExbColors.onPrimaryFill,
        secondary: ExbColors.lime,
        onSecondary: ExbColors.dark,
        outlineVariant: ExbColors.line,
        surface: ExbColors.paper,
        onSurface: ExbColors.dark,
      );
  final base = dark ? ThemeData.dark() : ThemeData.light();
  return ThemeData(
    useMaterial3: true,
    brightness: dark ? Brightness.dark : Brightness.light,
    colorScheme: scheme,
    scaffoldBackgroundColor: ExbColors.background,
    canvasColor: ExbColors.paper,
    cardColor: ExbColors.paper,
    fontFamily: 'Arial',
    textTheme: base.textTheme.apply(
      bodyColor: ExbColors.dark,
      displayColor: ExbColors.dark,
    ),
    iconTheme: IconThemeData(color: ExbColors.secondaryText),
    dividerColor: ExbColors.line,
    dividerTheme: DividerThemeData(color: ExbColors.line),
    popupMenuTheme: PopupMenuThemeData(color: ExbColors.paper),
    dialogTheme: DialogThemeData(backgroundColor: ExbColors.paper),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: dark ? ExbColors.story : const Color(0xFF203E31),
      contentTextStyle: TextStyle(color: dark ? ExbColors.dark : Colors.white),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: ExbColors.paper,
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: ExbColors.line),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(10),
        borderSide: BorderSide(color: ExbColors.line),
      ),
      labelStyle: TextStyle(color: ExbColors.secondaryText, fontSize: 13),
      hintStyle: TextStyle(color: ExbColors.muted),
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
        foregroundColor: ExbColors.green,
        side: BorderSide(color: ExbColors.line),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(foregroundColor: ExbColors.green),
    ),
    chipTheme: ChipThemeData(
      backgroundColor: ExbColors.story,
      side: BorderSide.none,
      labelStyle: TextStyle(color: ExbColors.green, fontSize: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
    ),
    tooltipTheme: const TooltipThemeData(
      waitDuration: Duration(milliseconds: 400),
    ),
  );
}
