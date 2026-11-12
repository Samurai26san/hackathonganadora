import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'core/auth/auth_controller.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/theme_mode.dart';
import 'features/admin/admin_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/dashboard/dashboard_screen.dart';
import 'features/gestiones/gestiones_screen.dart';
import 'features/reports/report_screen.dart';
import 'shared/widgets/juku_mascot.dart';
import 'shared/widgets/app_shell.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  // Web controls remain discoverable by assistive technology and keyboard tools.
  SemanticsBinding.instance.ensureSemantics();
  runApp(const ProviderScope(child: ExbApp()));
}

class RouterRefresh extends ChangeNotifier {
  void refresh() => notifyListeners();
}

/// Last visited route, restored when a theme change recreates the router.
String _lastLocation = '/dashboard';

final routerProvider = Provider<GoRouter>((ref) {
  // A new router remounts every page, so widgets reading ExbColors repaint.
  ref.watch(themeModeProvider);
  final refresh = RouterRefresh();
  ref.listen(authProvider, (_, next) => refresh.refresh());
  final router = GoRouter(
    initialLocation: _lastLocation,
    refreshListenable: refresh,
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      if (auth.isLoading) {
        return state.uri.path == '/loading' ? null : '/loading';
      }
      final user = auth.valueOrNull;
      if (user == null) return state.uri.path == '/login' ? null : '/login';
      if (state.uri.path == '/login' || state.uri.path == '/loading') {
        return '/dashboard';
      }
      if (state.uri.path == '/administracion' && !user.isAdmin) {
        return '/dashboard';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/loading',
        builder: (context, state) => const Scaffold(
          body: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                JukuMascot(JukuPose.corriendo, size: 150),
                SizedBox(height: 12),
                Text('Preparando tus finanzas…'),
              ],
            ),
          ),
        ),
      ),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/dashboard',
        builder: (context, state) =>
            AppShell(path: state.uri.path, child: const DashboardScreen()),
      ),
      GoRoute(
        path: '/presupuesto',
        builder: (context, state) => AppShell(
          path: state.uri.path,
          child: const ReportScreen(mode: 'budget'),
        ),
      ),
      GoRoute(
        path: '/reportes',
        builder: (context, state) => AppShell(
          path: state.uri.path,
          child: const ReportScreen(mode: 'reports'),
        ),
      ),
      GoRoute(
        path: '/movimientos',
        builder: (context, state) => AppShell(
          path: state.uri.path,
          child: const ReportScreen(mode: 'movements'),
        ),
      ),
      GoRoute(
        path: '/gestiones',
        builder: (context, state) =>
            AppShell(path: state.uri.path, child: const GestionesScreen()),
      ),
      GoRoute(
        path: '/administracion',
        builder: (context, state) =>
            AppShell(path: state.uri.path, child: const AdminScreen()),
      ),
      GoRoute(path: '/', redirect: (context, state) => '/dashboard'),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: FilledButton(
          onPressed: () => context.go('/dashboard'),
          child: const Text('Volver al panel financiero'),
        ),
      ),
    ),
  );
  ref.onDispose(() {
    final location = router.routeInformationProvider.value.uri.toString();
    if (location.startsWith('/') && location != '/loading') {
      _lastLocation = location;
    }
    router.dispose();
    refresh.dispose();
  });
  return router;
});

class ExbApp extends ConsumerWidget {
  const ExbApp({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mode = ref.watch(themeModeProvider);
    final dark =
        mode == ThemeMode.dark ||
        (mode == ThemeMode.system &&
            View.of(context).platformDispatcher.platformBrightness ==
                Brightness.dark);
    // appTheme also switches the ExbColors tokens read by every widget.
    final theme = appTheme(dark: dark);
    return MaterialApp.router(
      title: 'ExB Finanzas · Juku',
      debugShowCheckedModeBanner: false,
      theme: theme,
      locale: const Locale('es', 'BO'),
      supportedLocales: const [Locale('es', 'BO'), Locale('es'), Locale('en')],
      localizationsDelegates: GlobalMaterialLocalizations.delegates,
      routerConfig: ref.watch(routerProvider),
    );
  }
}
