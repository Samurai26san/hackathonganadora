import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/filters.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../dashboard/providers.dart';

final selectedReportProvider = StateProvider<String>((ref) => 'account');

class ReportScreen extends ConsumerWidget {
  const ReportScreen({super.key, required this.mode});
  final String mode;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final report = mode == 'budget'
        ? 'account'
        : mode == 'movements'
        ? 'movements'
        : ref.watch(selectedReportProvider);
    final data = ref.watch(reportProvider(report));
    final catalogs = ref.watch(catalogsProvider).valueOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Panel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (mode == 'reports' && catalogs != null) ...[
                DropdownButtonFormField<String>(
                  initialValue: report,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Tipo de reporte',
                  ),
                  items: catalogs.reports
                      .map(
                        (row) => DropdownMenuItem(
                          value: row['id'] as String,
                          child: Text(row['title'] as String),
                        ),
                      )
                      .toList(),
                  onChanged: (value) {
                    if (value != null) {
                      ref.read(selectedReportProvider.notifier).state = value;
                    }
                  },
                ),
                const SizedBox(height: 20),
              ],
              FilterBar(mode: mode),
            ],
          ),
        ),
        const SizedBox(height: 20),
        data.when(
          loading: () => const Padding(
            padding: EdgeInsets.all(60),
            child: Center(child: CircularProgressIndicator()),
          ),
          error: (error, _) => MessageState(
            title: 'No pudimos cargar el informe.',
            detail: '$error',
            onRetry: () => ref.invalidate(reportProvider(report)),
          ),
          data: (result) => Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              FinancialCards(summary: result.summary),
              const SizedBox(height: 20),
              if (report != 'movements') ...[
                Panel(
                  title: result.title,
                  subtitle: 'Presupuesto y ejecución · bolivianos (Bs)',
                  child: BookChart(
                    rows: result.rows,
                    dimension:
                        result.rows.firstOrNull?.labels.keys.firstOrNull ??
                        'rubro',
                  ),
                ),
                const SizedBox(height: 20),
              ],
              Panel(
                title: report == 'movements'
                    ? 'Cada movimiento, con su respaldo'
                    : 'Explora el detalle',
                subtitle:
                    'Selecciona una fila para consultar su desglose y origen.',
                action: ExportButton(report: report),
                child: ReportTable(
                  report: result,
                  onPage: (page) => ref.read(filtersProvider.notifier).state =
                      ref.read(filtersProvider).change('page', page),
                  onAccount: (id) {
                    ref.read(filtersProvider.notifier).state = ref
                        .read(filtersProvider)
                        .change('account', id);
                    context.go('/movimientos');
                  },
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class ExportButton extends ConsumerStatefulWidget {
  const ExportButton({
    super.key,
    required this.report,
    this.compareYear,
    this.filters,
  });
  final String report;
  final int? compareYear;
  final BudgetFilters? filters;
  @override
  ConsumerState<ExportButton> createState() => _ExportButtonState();
}

class _ExportButtonState extends ConsumerState<ExportButton> {
  bool busy = false;
  @override
  Widget build(BuildContext context) => PopupMenuButton<String>(
    enabled: !busy,
    tooltip: 'Exportar consulta filtrada',
    onSelected: (format) async {
      setState(() => busy = true);
      try {
        await ref
            .read(apiProvider)
            .export(
              widget.report,
              format,
              widget.filters ?? ref.read(filtersProvider),
              compareYear: widget.compareYear,
            );
      } catch (error) {
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(SnackBar(content: Text('$error')));
        }
      } finally {
        if (mounted) setState(() => busy = false);
      }
    },
    itemBuilder: (context) => [
      const PopupMenuItem(
        value: 'excel',
        child: Text('Descargar Excel (.xlsx)'),
      ),
      const PopupMenuItem(value: 'pdf', child: Text('Descargar PDF')),
      const PopupMenuItem(value: 'csv', child: Text('Descargar CSV')),
    ],
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        border: Border.all(color: ExbColors.line),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            busy ? Icons.hourglass_empty : Icons.file_download_outlined,
            size: 18,
            color: ExbColors.green,
          ),
          const SizedBox(width: 6),
          Text(
            busy ? 'Generando…' : 'Exportar',
            style: const TextStyle(fontSize: 12, color: ExbColors.green),
          ),
        ],
      ),
    ),
  );
}
