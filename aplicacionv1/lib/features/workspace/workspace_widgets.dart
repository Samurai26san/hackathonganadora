import 'package:flutter/material.dart';

void showFailure(BuildContext context, Object error) => ScaffoldMessenger.of(
  context,
).showSnackBar(SnackBar(content: Text('$error')));

Future<String?> askReason(BuildContext context, String title) async {
  final controller = TextEditingController();
  final key = GlobalKey<FormState>();
  final result = await showDialog<String>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Form(
        key: key,
        child: TextFormField(
          controller: controller,
          autofocus: true,
          maxLength: 1000,
          decoration: const InputDecoration(labelText: 'Motivo de la acción'),
          validator: (v) => (v ?? '').trim().length < 5
              ? 'Escribe al menos cinco caracteres.'
              : null,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () {
            if (key.currentState!.validate())
              Navigator.pop(context, controller.text.trim());
          },
          child: const Text('Confirmar'),
        ),
      ],
    ),
  );
  controller.dispose();
  return result;
}

class ReportTree extends StatelessWidget {
  const ReportTree(this.data, {super.key});
  final dynamic data;
  @override
  Widget build(BuildContext context) {
    if (data is Map)
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final entry in (data as Map).entries)
            if (entry.value is Map || entry.value is List)
              Card(
                child: ExpansionTile(
                  title: Text(_name('${entry.key}')),
                  childrenPadding: const EdgeInsets.all(12),
                  children: [ReportTree(entry.value)],
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.symmetric(
                  vertical: 5,
                  horizontal: 12,
                ),
                child: Text(
                  '${_name('${entry.key}')}: ${entry.value ?? 'Sin datos'}',
                ),
              ),
        ],
      );
    if (data is List)
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: (data as List).isEmpty
            ? [const Text('Sin datos registrados')]
            : [
                for (final item in data as List)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: ReportTree(item),
                  ),
              ],
      );
    return Text('$data');
  }

  String _name(String key) =>
      const {
        'executive_summary': 'Resumen ejecutivo',
        'risks': 'Alertas de riesgo',
        'scope': 'Alcance y filtros',
        'budget_execution': 'Ejecución presupuestaria',
        'financial_statements': 'Estados financieros',
        'data_quality': 'Calidad de datos',
        'limitations': 'Alcance y limitaciones',
        'balance': 'Situación patrimonial',
        'income_statement': 'Estado de resultados',
        'equity_changes': 'Cambios en el patrimonio',
        'cash_flow': 'Flujos de efectivo',
        'notes': 'Notas a los estados financieros',
        'auditor': 'Dictamen del auditor',
        'iue_estimate': 'Estimación parametrizada de IUE',
        'asset': 'Activo',
        'liability': 'Pasivo',
        'equity_total': 'Patrimonio total',
        'difference': 'Diferencia',
        'balanced': 'Balance cuadrado',
        'net_result': 'Utilidad neta',
        'operating_result': 'Resultado operativo',
        'gross_result': 'Resultado bruto',
        'iue_recorded': 'IUE registrado',
        'previous_year': 'Comparación con gestión anterior',
        'ledger': 'Libro diario',
        'accounts': 'Cuentas',
        'summary': 'Indicadores',
        'cutoff': 'Fecha de corte',
        'currency': 'Moneda',
        'period_start': 'Inicio del período',
        'regulatory_status': 'Estado del documento',
      }[key] ??
      key.replaceAll('_', ' ');
}
