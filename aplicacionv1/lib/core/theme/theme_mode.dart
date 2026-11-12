import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/platform_stub.dart'
    if (dart.library.js_interop) '../api/platform_web.dart';

const _key = 'exb.theme';

/// Day/night preference: follows the device until the user picks one.
final themeModeProvider = StateNotifierProvider<ThemeModeController, ThemeMode>(
  (ref) => ThemeModeController(),
);

class ThemeModeController extends StateNotifier<ThemeMode> {
  ThemeModeController()
    : super(switch (readSetting(_key)) {
        'dark' => ThemeMode.dark,
        'light' => ThemeMode.light,
        _ => ThemeMode.system,
      });

  void toggle({required bool currentlyDark}) {
    state = currentlyDark ? ThemeMode.light : ThemeMode.dark;
    writeSetting(_key, state.name);
  }
}

/// Moon/sun switch shared by the login screen and the app header.
class ThemeToggle extends ConsumerWidget {
  const ThemeToggle({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return IconButton(
      tooltip: dark ? 'Cambiar a modo día' : 'Cambiar a modo noche',
      onPressed: () =>
          ref.read(themeModeProvider.notifier).toggle(currentlyDark: dark),
      icon: Icon(dark ? Icons.light_mode_outlined : Icons.dark_mode_outlined),
    );
  }
}
