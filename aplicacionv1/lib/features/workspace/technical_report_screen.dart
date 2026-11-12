import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../dashboard/providers.dart';
import 'workspace_widgets.dart';

class TechnicalReportScreen extends ConsumerStatefulWidget {
  const TechnicalReportScreen({super.key});
  @override
  ConsumerState<TechnicalReportScreen> createState() =>
      _TechnicalReportScreenState();
}

class _TechnicalReportScreenState extends ConsumerState<TechnicalReportScreen> {
  String period = 'monthly';
  int year = DateTime.now().year, month = DateTime.now().month;
  bool validated = true, busy = false;
  final base = TextEditingController(), rate = TextEditingController();
  Json? result;
  @override
  void initState() {
    super.initState();
    year = ref.read(filtersProvider).year;
  }

  @override
  void dispose() {
    base.dispose();
    rate.dispose();
    super.dispose();
  }

  Future<void> generate(String format) async {
    setState(() => busy = true);
    final body = <String, dynamic>{
      'periodicity': period,
      'year': year,
      'month': month,
      'validated_only': validated,
      'format': format,
      if (base.text.trim().isNotEmpty) 'iue_base': base.text.trim(),
      if (rate.text.trim().isNotEmpty) 'iue_rate': rate.text.trim(),
    };
    try {
      if ((base.text.trim().isEmpty) != (rate.text.trim().isEmpty))
        throw const ApiError('Indica base y tasa juntas para estimar el IUE.');
      if (format == 'json') {
        final report =
            await ref
                    .read(apiProvider)
                    .post('technical-reports/generate', data: body)
                as Json;
        if (mounted) setState(() => result = report);
      } else {
        await ref
            .read(apiProvider)
            .downloadDocument(
              'technical-reports/generate',
              body,
              'informe-tecnico-$year.${format == 'excel' ? 'xlsx' : 'pdf'}',
            );
      }
    } catch (e) {
      if (mounted) showFailure(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final years = ref.watch(catalogsProvider).valueOrNull?.years ?? [year];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Genera un borrador técnico con ejecución, comparativas, los seis bloques contables y calidad de datos. Los estados institucionales requieren alcance completo.',
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 16,
          children: [
            SizedBox(
              width: 260,
              child: DropdownButtonFormField<String>(
                initialValue: period,
                decoration: const InputDecoration(labelText: 'Periodicidad'),
                items: const [
                  DropdownMenuItem(
                    value: 'monthly',
                    child: Text('Corte mensual acumulado'),
                  ),
                  DropdownMenuItem(
                    value: 'annual',
                    child: Text('Cierre anual comparativo'),
                  ),
                ],
                onChanged: busy ? null : (v) => setState(() => period = v!),
              ),
            ),
            SizedBox(
              width: 160,
              child: DropdownButtonFormField<int>(
                initialValue: years.contains(year) ? year : years.first,
                decoration: const InputDecoration(labelText: 'Gestión'),
                items: [
                  for (final y in years)
                    DropdownMenuItem(value: y, child: Text('$y')),
                ],
                onChanged: busy ? null : (v) => setState(() => year = v!),
              ),
            ),
            if (period == 'monthly')
              SizedBox(
                width: 160,
                child: DropdownButtonFormField<int>(
                  initialValue: month,
                  decoration: const InputDecoration(labelText: 'Mes de corte'),
                  items: [
                    for (var i = 1; i <= 12; i++)
                      DropdownMenuItem(value: i, child: Text('$i')),
                  ],
                  onChanged: busy ? null : (v) => setState(() => month = v!),
                ),
              ),
          ],
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('Solo filas validadas y consolidadas'),
          subtitle: const Text(
            'El Excel histórico no se considera validación manual. Desactiva para incluir todos los hechos registrados.',
          ),
          value: validated,
          onChanged: busy ? null : (v) => setState(() => validated = v),
        ),
        ExpansionTile(
          title: const Text('Estimación opcional de IUE'),
          subtitle: const Text(
            'La estimación no modifica el IUE contabilizado.',
          ),
          children: [
            Wrap(
              spacing: 16,
              runSpacing: 12,
              children: [
                SizedBox(
                  width: 240,
                  child: TextField(
                    controller: base,
                    decoration: const InputDecoration(
                      labelText: 'Base imponible proporcionada (BOB)',
                    ),
                  ),
                ),
                SizedBox(
                  width: 240,
                  child: TextField(
                    controller: rate,
                    decoration: const InputDecoration(
                      labelText: 'Tasa aplicable proporcionada (%)',
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            FilledButton.icon(
              onPressed: busy ? null : () => generate('json'),
              icon: const Icon(Icons.description_outlined),
              label: const Text('Generar informe'),
            ),
            OutlinedButton.icon(
              onPressed: busy ? null : () => generate('pdf'),
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: const Text('Descargar PDF'),
            ),
            OutlinedButton.icon(
              onPressed: busy ? null : () => generate('excel'),
              icon: const Icon(Icons.table_chart_outlined),
              label: const Text('Descargar Excel con fórmulas'),
            ),
          ],
        ),
        if (busy)
          const Padding(
            padding: EdgeInsets.all(16),
            child: LinearProgressIndicator(),
          ),
        const SizedBox(height: 20),
        if (result != null) ReportTree(result),
      ],
    );
  }
}
