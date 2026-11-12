import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/money.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../../shared/widgets/filters.dart';
import 'providers.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final result = ref.watch(reportProvider('summary'));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const FilterBar(mode: 'dashboard'),
        const SizedBox(height: 24),
        ...ref
            .watch(riskAlertsProvider)
            .maybeWhen(
              data: (alerts) => [
                for (final alert in alerts)
                  Card(
                    child: ListTile(
                      leading: Icon(
                        Icons.warning_amber_rounded,
                        color: alert['risk'] == 'high'
                            ? Colors.red
                            : Colors.orange,
                      ),
                      title: Text('${alert['title']}'),
                      subtitle: Text(
                        'Riesgo ${alert['risk'] == 'high' ? 'alto' : 'medio'} · Dictámenes y notas contables',
                      ),
                      onTap: () => context.go('/contabilidad'),
                    ),
                  ),
              ],
              orElse: () => <Widget>[],
            ),
        result.when(
          loading: () => const Padding(
            padding: EdgeInsets.all(80),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (error, _) => MessageState(
            title: 'No pudimos consultar la gestión.',
            detail: '$error',
            onRetry: () => ref.invalidate(reportProvider('summary')),
          ),
          data: (report) => Column(
            children: [
              FinancialCards(summary: report.summary),
              const SizedBox(height: 24),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth > 950;
                  final rubric = Panel(
                    title: 'Ejecución por rubro',
                    subtitle:
                        'De una mirada general al detalle de cada cuenta.',
                    action: TextButton(
                      onPressed: () => context.go('/presupuesto'),
                      child: const Text(
                        'Ver detalle ↗',
                        style: TextStyle(fontSize: 11),
                      ),
                    ),
                    child: BookChart(
                      rows: report.rows,
                      dimension: 'rubro',
                      onSelect: (row) {
                        ref.read(filtersProvider.notifier).state = ref
                            .read(filtersProvider)
                            .change('rubro', row.dimensions['rubro']);
                        context.go('/presupuesto');
                      },
                    ),
                  );
                  final monthly = Panel(
                    title: 'El año, mes a mes',
                    subtitle: 'Ejecución según el mes original de BD.',
                    child: ref
                        .watch(reportProvider('monthly'))
                        .when(
                          loading: () => const SizedBox(
                            height: 270,
                            child: Center(child: CircularProgressIndicator()),
                          ),
                          error: (error, _) => MessageState(
                            title: 'Serie mensual no disponible',
                            detail: '$error',
                          ),
                          data: (value) => BookChart(
                            rows: value.rows
                                .where((row) => row.labels['month'] != 'PTTO')
                                .toList(),
                            dimension: 'month',
                            height: 270,
                          ),
                        ),
                  );
                  return wide
                      ? Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(flex: 3, child: rubric),
                            const SizedBox(width: 20),
                            Expanded(flex: 2, child: monthly),
                          ],
                        )
                      : Column(
                          children: [
                            rubric,
                            const SizedBox(height: 20),
                            monthly,
                          ],
                        );
                },
              ),
              const SizedBox(height: 24),
              LayoutBuilder(
                builder: (context, constraints) => Wrap(
                  spacing: 16,
                  runSpacing: 16,
                  children: [
                    for (final item in [
                      (
                        'Presupuesto',
                        'Lo asignado, lo ejecutado y lo disponible.',
                        Icons.account_balance_wallet_outlined,
                        '/presupuesto',
                      ),
                      (
                        'Reportes',
                        'Siete maneras de entender tus datos.',
                        Icons.insert_chart_outlined,
                        '/reportes',
                      ),
                      (
                        'Movimientos',
                        'Cada transacción tiene una historia.',
                        Icons.receipt_long_outlined,
                        '/movimientos',
                      ),
                      (
                        'Gestiones',
                        'Un mismo lugar para todo el histórico.',
                        Icons.calendar_month_outlined,
                        '/gestiones',
                      ),
                    ])
                      SizedBox(
                        width: constraints.maxWidth < 600
                            ? constraints.maxWidth
                            : (constraints.maxWidth - 16) / 2,
                        child: Material(
                          color: ExbColors.paper,
                          borderRadius: BorderRadius.circular(14),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(14),
                            onTap: () => context.go(item.$4),
                            child: Container(
                              padding: const EdgeInsets.all(22),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: ExbColors.line),
                              ),
                              child: Row(
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      color: ExbColors.story,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Icon(
                                      item.$3,
                                      color: ExbColors.green,
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          item.$1,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          item.$2,
                                          style: const TextStyle(
                                            fontSize: 12,
                                            color: ExbColors.secondaryText,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const Icon(Icons.north_east, size: 18),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Panel(
                title: 'Tu información tiene una fuente',
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.verified_outlined, color: ExbColors.green),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Text(
                        'Excel institucional · Hoja BD · Gestión ${ref.watch(filtersProvider).year}\nÚltimo movimiento: ${report.metadata['cutoff_date'] ?? 'sin movimientos'}\nPresupuesto vigente ${report.summary['current_budget']?.currency ?? Money.zero.currency}. Las consultas y exportaciones usan la misma fuente y los mismos filtros.',
                        style: const TextStyle(
                          height: 1.7,
                          fontSize: 12,
                          color: ExbColors.secondaryText,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
