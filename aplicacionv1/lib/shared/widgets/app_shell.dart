import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/models.dart';
import '../../core/auth/auth_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../features/chat/chat_controller.dart';
import '../../features/chat/juku_panel.dart';
import '../../features/dashboard/providers.dart';
import '../../features/reports/report_screen.dart';

const navigation = [
  ('Panel financiero', '/dashboard', Icons.space_dashboard_outlined),
  ('Presupuesto', '/presupuesto', Icons.account_balance_wallet_outlined),
  ('Reportes', '/reportes', Icons.bar_chart_outlined),
  ('Movimientos', '/movimientos', Icons.receipt_long_outlined),
  ('Gestiones', '/gestiones', Icons.calendar_month_outlined),
];
const descriptions = {
  '/dashboard': (
    'TU GESTIÓN, DE UN VISTAZO',
    'Panel financiero',
    'Presupuesto, ejecución y saldo. Todo conectado en una sola mirada.',
  ),
  '/presupuesto': (
    'CADA RECURSO CUENTA',
    'Presupuesto',
    'Cuánto se ha asignado, cuánto se ha gastado y cuánto queda disponible.',
  ),
  '/reportes': (
    'DE LOS DATOS A LAS DECISIONES',
    'Reportes',
    'Siete formas de explorar tu información y generar resultados.',
  ),
  '/movimientos': (
    'EL DETALLE DETRÁS DE CADA CIFRA',
    'Movimientos',
    'Encuentra cada transacción y consulta su respaldo contable.',
  ),
  '/gestiones': (
    'UNA MIRADA AL HISTÓRICO',
    'Gestiones',
    'Compara la evolución financiera entre los años disponibles.',
  ),
  '/administracion': (
    'INFORMACIÓN CON TRAZABILIDAD',
    'Administración',
    'Cuentas, alcances, fuentes y registros institucionales.',
  ),
};

final chatOpenProvider = StateProvider<bool>((ref) => false);

class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key, required this.child, required this.path});
  final Widget child;
  final String path;
  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  bool sidebar = true;
  final scaffold = GlobalKey<ScaffoldState>();
  @override
  Widget build(BuildContext context) {
    final chat = ref.watch(chatOpenProvider);
    final user = ref.watch(authProvider).valueOrNull;
    final filters = ref.watch(filtersProvider);
    final catalog = ref.watch(catalogsProvider);
    ref.listen(catalogsProvider, (_, value) {
      final years = value.valueOrNull?.years ?? [];
      if (years.isNotEmpty && !years.contains(ref.read(filtersProvider).year)) {
        ref.read(filtersProvider.notifier).state = BudgetFilters(
          year: years.first,
        );
      }
    });
    final desc = descriptions[widget.path] ?? descriptions['/dashboard']!;
    return LayoutBuilder(
      builder: (context, constraints) {
        final desktop = constraints.maxWidth >= 1000;
        final dockChat = chat && constraints.maxWidth >= 1400;
        final side = _sidebar(user);
        return Scaffold(
          key: scaffold,
          drawer: desktop ? null : Drawer(width: 240, child: side),
          body: Stack(
            children: [
              Row(
                children: [
                  if (desktop && sidebar) SizedBox(width: 228, child: side),
                  Expanded(
                    child: Column(
                      children: [
                        Container(
                          height: 82,
                          padding: EdgeInsets.symmetric(
                            horizontal: desktop ? 30 : 12,
                          ),
                          decoration: const BoxDecoration(
                            color: Colors.white,
                            border: Border(
                              bottom: BorderSide(color: ExbColors.line),
                            ),
                          ),
                          child: Row(
                            children: [
                              IconButton(
                                tooltip: 'Abrir o cerrar menú',
                                onPressed: () {
                                  if (desktop) {
                                    setState(() => sidebar = !sidebar);
                                  } else {
                                    scaffold.currentState!.openDrawer();
                                  }
                                },
                                icon: const Icon(Icons.menu, size: 22),
                              ),
                              const SizedBox(width: 12),
                              if (!desktop || !sidebar) ...[
                                Image.asset(
                                  'assets/images/logo-ensena-bolivia.png',
                                  width: desktop ? 110 : 84,
                                ),
                                const SizedBox(width: 20),
                              ],
                              if (constraints.maxWidth > 600) ...[
                                const Text(
                                  '/',
                                  style: TextStyle(
                                    color: ExbColors.line,
                                    fontSize: 24,
                                  ),
                                ),
                                const SizedBox(width: 20),
                                Expanded(
                                  child: Text(
                                    desc.$2,
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: ExbColors.secondaryText,
                                    ),
                                  ),
                                ),
                              ] else
                                const Spacer(),
                              if (constraints.maxWidth > 700)
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 12,
                                    vertical: 7,
                                  ),
                                  decoration: BoxDecoration(
                                    color: ExbColors.background,
                                    borderRadius: BorderRadius.circular(20),
                                  ),
                                  child: const Text(
                                    '● DATOS DEL EXCEL',
                                    style: TextStyle(
                                      fontSize: 9,
                                      letterSpacing: 1,
                                      color: ExbColors.green,
                                    ),
                                  ),
                                ),
                              if (user?.isAdmin ?? false)
                                IconButton(
                                  tooltip: 'Administración',
                                  onPressed: () =>
                                      context.go('/administracion'),
                                  icon: const Icon(
                                    Icons.settings_outlined,
                                    size: 20,
                                  ),
                                ),
                              IconButton(
                                tooltip: 'Ayuda',
                                onPressed: () => showDialog<void>(
                                  context: context,
                                  builder: (context) => AlertDialog(
                                    title: const Text(
                                      'Tu gestión, paso a paso',
                                    ),
                                    content: const Text(
                                      'Selecciona una gestión y financiador. Explora los rubros para abrir sus cuentas y movimientos. En Reportes encontrarás los siete informes. Pregúntale a Juku para consultar cifras verificadas o documentos institucionales.',
                                    ),
                                    actions: [
                                      TextButton(
                                        onPressed: () => Navigator.pop(context),
                                        child: const Text('Entendido'),
                                      ),
                                    ],
                                  ),
                                ),
                                icon: const Icon(Icons.help_outline, size: 20),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: Row(
                            children: [
                              Expanded(
                                child: SelectionArea(
                                  child: SingleChildScrollView(
                                    key: ValueKey(widget.path),
                                    padding: EdgeInsets.fromLTRB(
                                      desktop ? 36 : 18,
                                      32,
                                      desktop ? 36 : 18,
                                      130,
                                    ),
                                    child: Center(
                                      child: ConstrainedBox(
                                        constraints: const BoxConstraints(
                                          maxWidth: 1500,
                                        ),
                                        child: Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.start,
                                          children: [
                                            Wrap(
                                              spacing: 28,
                                              runSpacing: 20,
                                              crossAxisAlignment:
                                                  WrapCrossAlignment.center,
                                              children: [
                                                Column(
                                                  crossAxisAlignment:
                                                      CrossAxisAlignment.start,
                                                  children: [
                                                    Text(
                                                      desc.$1,
                                                      style: const TextStyle(
                                                        fontSize: 10,
                                                        letterSpacing: 1.8,
                                                        color: ExbColors.green,
                                                        fontWeight:
                                                            FontWeight.w700,
                                                      ),
                                                    ),
                                                    const SizedBox(height: 10),
                                                    Text(
                                                      desc.$2,
                                                      style: const TextStyle(
                                                        fontSize: 32,
                                                        letterSpacing: -1,
                                                        fontWeight:
                                                            FontWeight.w700,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                                Container(
                                                  padding:
                                                      const EdgeInsets.symmetric(
                                                        horizontal: 14,
                                                        vertical: 8,
                                                      ),
                                                  decoration: BoxDecoration(
                                                    color: ExbColors.story,
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                          8,
                                                        ),
                                                  ),
                                                  child: Text(
                                                    'Gestión ${filters.year}',
                                                    style: const TextStyle(
                                                      fontSize: 12,
                                                      color: ExbColors.green,
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ),
                                            const SizedBox(height: 12),
                                            Text(
                                              desc.$3,
                                              style: const TextStyle(
                                                fontSize: 13,
                                                color: ExbColors.secondaryText,
                                                height: 1.6,
                                              ),
                                            ),
                                            const SizedBox(height: 30),
                                            if (catalog.isLoading)
                                              const LinearProgressIndicator()
                                            else if (catalog.hasError)
                                              Padding(
                                                padding: const EdgeInsets.only(
                                                  bottom: 20,
                                                ),
                                                child: Row(
                                                  children: [
                                                    const Icon(
                                                      Icons.cloud_off_outlined,
                                                      color: ExbColors.amber,
                                                    ),
                                                    const SizedBox(width: 10),
                                                    Expanded(
                                                      child: Text(
                                                        '${catalog.error}',
                                                        style: const TextStyle(
                                                          color:
                                                              ExbColors.amber,
                                                        ),
                                                      ),
                                                    ),
                                                    TextButton(
                                                      onPressed: () =>
                                                          ref.invalidate(
                                                            catalogsProvider,
                                                          ),
                                                      child: const Text(
                                                        'Reintentar',
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              ),
                                            widget.child,
                                            const SizedBox(height: 36),
                                            const Divider(),
                                            const SizedBox(height: 12),
                                            const Text(
                                              'Fuente: Excel institucional · Hoja BD. Importes en bolivianos (Bs).\nLas consultas respetan los filtros activos y el alcance de tu cuenta.',
                                              style: TextStyle(
                                                fontSize: 10,
                                                height: 1.7,
                                                color: ExbColors.secondaryText,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                              if (dockChat)
                                SizedBox(
                                  width: 420,
                                  child: JukuPanel(
                                    onClose: () =>
                                        ref
                                                .read(chatOpenProvider.notifier)
                                                .state =
                                            false,
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (chat && !dockChat)
                Positioned(
                  top: 82,
                  bottom: 0,
                  right: 0,
                  width: math.min(420, constraints.maxWidth),
                  child: JukuPanel(
                    onClose: () =>
                        ref.read(chatOpenProvider.notifier).state = false,
                  ),
                ),
              if (!chat)
                Positioned(
                  right: 24,
                  bottom: 20,
                  child: Semantics(
                    button: true,
                    label: 'Abrir asistente Juku',
                    child: Material(
                      color: Colors.white,
                      elevation: 4,
                      shadowColor: ExbColors.green.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(18),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(18),
                        onTap: () =>
                            ref.read(chatOpenProvider.notifier).state = true,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(18, 10, 12, 10),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    '¿Lo vemos juntos?',
                                    style: TextStyle(
                                      fontSize: 13,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  SizedBox(height: 4),
                                  Text(
                                    'Pregúntale a Juku',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: ExbColors.secondaryText,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(width: 12),
                              SvgPicture.asset(
                                'assets/icons/juku.svg',
                                height: 66,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _sidebar(AppUser? user) => Material(
    color: Colors.white,
    child: Container(
      decoration: const BoxDecoration(
        border: Border(right: BorderSide(color: ExbColors.line)),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Image.asset(
              'assets/images/logo-ensena-bolivia.png',
              width: 170,
            ),
          ),
          const SizedBox(height: 12),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              'FINANZAS',
              style: TextStyle(
                fontSize: 10,
                letterSpacing: 2.8,
                color: ExbColors.secondaryText,
              ),
            ),
          ),
          const SizedBox(height: 42),
          for (final item in navigation)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: ListTile(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(10),
                ),
                selected: widget.path == item.$2,
                selectedTileColor: ExbColors.story,
                selectedColor: ExbColors.green,
                textColor: ExbColors.secondaryText,
                iconColor: ExbColors.secondaryText,
                dense: true,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 5,
                ),
                leading: Icon(item.$3, size: 20),
                title: Text(item.$1, style: const TextStyle(fontSize: 12)),
                onTap: () {
                  context.go(item.$2);
                  scaffold.currentState?.closeDrawer();
                },
              ),
            ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: ExbColors.background,
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.lock_outline, color: ExbColors.green, size: 18),
                SizedBox(height: 10),
                Text(
                  'Información institucional',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
                ),
                SizedBox(height: 6),
                Text(
                  'Tu acceso y cada consulta tienen trazabilidad.',
                  style: TextStyle(
                    fontSize: 10,
                    height: 1.6,
                    color: ExbColors.secondaryText,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 22),
          const Divider(),
          const SizedBox(height: 12),
          Row(
            children: [
              CircleAvatar(
                radius: 17,
                backgroundColor: ExbColors.story,
                child: Text(
                  user?.name.substring(0, 1) ?? 'E',
                  style: const TextStyle(fontSize: 12, color: ExbColors.green),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      user?.name ?? '',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      user?.roleLabel ?? '',
                      style: const TextStyle(
                        fontSize: 10,
                        color: ExbColors.secondaryText,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                tooltip: 'Cerrar sesión',
                onPressed: () async {
                  try {
                    await ref.read(authProvider.notifier).logout();
                    ref.invalidate(chatProvider);
                    ref.invalidate(catalogsProvider);
                    ref.invalidate(filtersProvider);
                    ref.invalidate(selectedReportProvider);
                  } catch (error) {
                    if (mounted) {
                      ScaffoldMessenger.of(
                        context,
                      ).showSnackBar(SnackBar(content: Text('$error')));
                    }
                  }
                },
                icon: const Icon(Icons.logout, size: 18),
              ),
            ],
          ),
        ],
      ),
    ),
  );
}
