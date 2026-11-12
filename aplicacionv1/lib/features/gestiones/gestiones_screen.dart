import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../../shared/widgets/filters.dart';
import '../dashboard/providers.dart';
import '../reports/report_screen.dart';

class GestionesScreen extends ConsumerStatefulWidget {
  const GestionesScreen({super.key});
  @override
  ConsumerState<GestionesScreen> createState() => _GestionesScreenState();
}

class _GestionesScreenState extends ConsumerState<GestionesScreen> {
  int? otherYear;
  Future<FinancialReport>? comparison;
  @override
  Widget build(BuildContext context) {
    final catalogs = ref.watch(catalogsProvider).valueOrNull;
    final filters = ref.watch(filtersProvider);
    final years = catalogs?.years ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Panel(
          title: 'Un histórico que crece contigo',
          subtitle:
              'Compara únicamente gestiones con datos institucionales disponibles.',
          child: Wrap(
            spacing: 16,
            runSpacing: 16,
            crossAxisAlignment: WrapCrossAlignment.end,
            children: [
              FilterSelect(
                label: 'Gestión inicial',
                value: filters.year,
                allowAll: false,
                items: years.map((year) => CatalogItem(year, '$year')).toList(),
                onChanged: (year) {
                  if (year != null) {
                    ref.read(filtersProvider.notifier).state = filters.change(
                      'year',
                      year,
                    );
                    setState(() => comparison = null);
                  }
                },
              ),
              FilterSelect(
                label: 'Gestión final',
                value: otherYear,
                allowAll: false,
                items: years
                    .where((year) => year != filters.year)
                    .map((year) => CatalogItem(year, '$year'))
                    .toList(),
                onChanged: (year) => setState(() {
                  otherYear = year;
                  comparison = null;
                }),
              ),
              SizedBox(
                width: 210,
                child: DropdownButtonFormField<String>(
                  isExpanded: true,
                  initialValue: filters.metric,
                  decoration: const InputDecoration(
                    labelText: 'Indicador a comparar',
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'executed',
                      child: Text('Ejecución'),
                    ),
                    DropdownMenuItem(
                      value: 'current_budget',
                      child: Text('Presupuesto vigente'),
                    ),
                    DropdownMenuItem(
                      value: 'balance',
                      child: Text('Saldo disponible'),
                    ),
                    DropdownMenuItem(
                      value: 'execution_percentage',
                      child: Text('Porcentaje de ejecución'),
                    ),
                  ],
                  onChanged: (value) {
                    if (value != null) {
                      ref.read(filtersProvider.notifier).state = filters.change(
                        'metric',
                        value,
                      );
                      setState(() => comparison = null);
                    }
                  },
                ),
              ),
              FilledButton.icon(
                onPressed: otherYear == null || otherYear == filters.year
                    ? null
                    : () => setState(
                        () => comparison = ref
                            .read(apiProvider)
                            .report('compare', filters, compareYear: otherYear),
                      ),
                icon: const Icon(Icons.compare_arrows),
                label: const Text('Comparar'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        if (years.length < 2)
          MessageState(
            icon: Icons.calendar_month_outlined,
            title: 'Por ahora, una gestión. Sin comparaciones inventadas.',
            detail:
                'El archivo proporcionado contiene únicamente ${years.firstOrNull ?? 2026}. Cuando se incorpore otra gestión real, podrás consultar sus diferencias aquí.',
          ),
        if (comparison != null)
          FutureBuilder<FinancialReport>(
            future: comparison,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return MessageState(
                  title: 'No se pudo comparar',
                  detail: '${snapshot.error}',
                );
              }
              final report = snapshot.data!;
              return Panel(
                title: report.title,
                action: ExportButton(report: 'compare', compareYear: otherYear),
                child: Column(
                  children: [
                    BookChart(rows: report.rows, dimension: 'year'),
                    const SizedBox(height: 24),
                    ReportTable(report: report),
                  ],
                ),
              );
            },
          ),
      ],
    );
  }
}
