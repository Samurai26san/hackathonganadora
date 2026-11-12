import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../../core/api/models.dart';
import '../../core/theme/app_theme.dart';
import '../../core/utils/money.dart';

class Panel extends StatelessWidget {
  const Panel({
    super.key,
    this.title,
    this.subtitle,
    this.action,
    required this.child,
    this.padding = 24,
  });
  final String? title, subtitle;
  final Widget? action;
  final Widget child;
  final double padding;
  @override
  Widget build(BuildContext context) => Material(
    color: ExbColors.paper,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(17),
      side: const BorderSide(color: ExbColors.line),
    ),
    child: Padding(
      padding: EdgeInsets.all(padding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title!,
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 17,
                        ),
                      ),
                      if (subtitle != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text(
                            subtitle!,
                            style: const TextStyle(
                              fontSize: 12,
                              color: ExbColors.secondaryText,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                ?action,
              ],
            ),
            const SizedBox(height: 24),
          ],
          child,
        ],
      ),
    ),
  );
}

class MessageState extends StatelessWidget {
  const MessageState({
    super.key,
    required this.title,
    this.detail,
    this.onRetry,
    this.icon = Icons.info_outline,
  });
  final String title;
  final String? detail;
  final VoidCallback? onRetry;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.all(32),
    child: Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: ExbColors.green, size: 36),
          const SizedBox(height: 16),
          Text(
            title,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
          ),
          if (detail != null)
            Padding(
              padding: const EdgeInsets.only(top: 10),
              child: Text(
                detail!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: ExbColors.secondaryText),
              ),
            ),
          if (onRetry != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh),
                label: const Text('Volver a intentar'),
              ),
            ),
        ],
      ),
    ),
  );
}

class FinancialCards extends StatelessWidget {
  const FinancialCards({super.key, required this.summary});
  final Map<String, Money> summary;
  @override
  Widget build(BuildContext context) {
    final cards = [
      (
        'Presupuesto vigente',
        'current_budget',
        Icons.account_balance_outlined,
        'Inicial + modificaciones',
      ),
      (
        'Ejecución acumulada',
        'executed',
        Icons.trending_up,
        'Movimientos de la hoja BD',
      ),
      (
        'Saldo disponible',
        'balance',
        Icons.savings_outlined,
        'Presupuesto menos ejecución',
      ),
      (
        'Porcentaje de ejecución',
        'execution_percentage',
        Icons.donut_large_outlined,
        'Sobre el presupuesto vigente',
      ),
    ];
    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 1) return const SizedBox.shrink();
        final columns = constraints.maxWidth < 620 ? 2 : 4;
        final width = (constraints.maxWidth - (columns - 1) * 14) / columns;
        return Wrap(
          spacing: 14,
          runSpacing: 14,
          children: cards.map((card) {
            final value = summary[card.$2] ?? Money.zero;
            final percent = card.$2 == 'execution_percentage';
            return SizedBox(
              width: width,
              child: Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: percent ? ExbColors.story : Colors.white,
                  border: Border.all(color: ExbColors.line),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(card.$3, color: ExbColors.green, size: 19),
                        const Spacer(),
                        if (percent)
                          const Icon(
                            Icons.north_east,
                            size: 16,
                            color: ExbColors.green,
                          ),
                      ],
                    ),
                    const SizedBox(height: 18),
                    Text(
                      card.$1,
                      style: const TextStyle(
                        fontSize: 12,
                        color: ExbColors.secondaryText,
                      ),
                    ),
                    const SizedBox(height: 8),
                    FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        percent ? '${value.formatted} %' : value.currency,
                        style: TextStyle(
                          fontSize: 26,
                          letterSpacing: -0.8,
                          fontWeight: FontWeight.w700,
                          color: value.cents < 0
                              ? ExbColors.amber
                              : ExbColors.dark,
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      card.$4,
                      style: const TextStyle(
                        fontSize: 10,
                        color: ExbColors.secondaryText,
                      ),
                    ),
                  ],
                ),
              ),
            );
          }).toList(),
        );
      },
    );
  }
}

class BookChart extends StatelessWidget {
  const BookChart({
    super.key,
    required this.rows,
    required this.dimension,
    this.onSelect,
    this.height = 270,
  });
  final List<FinancialRow> rows;
  final String dimension;
  final void Function(FinancialRow)? onSelect;
  final double height;
  @override
  Widget build(BuildContext context) {
    final grouped = <String, FinancialRow>{};
    for (final row in rows) {
      final label =
          row.labels[dimension] ?? row.labels.values.firstOrNull ?? '';
      final existing = grouped[label];
      if (existing == null) {
        grouped[label] = FinancialRow(
          labels: {dimension: label},
          dimensions: row.dimensions,
          values: Map.of(row.values),
        );
      } else {
        for (final key in ['current_budget', 'executed']) {
          existing.values[key] =
              (existing.values[key] ?? Money.zero) +
              (row.values[key] ?? Money.zero);
        }
      }
    }
    if (grouped.isEmpty) {
      return const MessageState(title: 'No hay datos para estos filtros.');
    }
    final maxCents = grouped.values.fold<int>(
      1,
      (max_, row) => math.max(
        max_,
        math.max(
          (row.values['current_budget'] ?? Money.zero).cents.abs(),
          (row.values['executed'] ?? Money.zero).cents.abs(),
        ),
      ),
    );
    return Column(
      children: [
        const Wrap(
          spacing: 20,
          children: [
            Legend(color: ExbColors.books, label: 'Presupuesto'),
            Legend(color: ExbColors.execution, label: 'Ejecutado'),
          ],
        ),
        const SizedBox(height: 16),
        SizedBox(
          height: height,
          child: LayoutBuilder(
            builder: (context, constraints) {
              final width = math.max(
                108.0,
                constraints.maxWidth / grouped.length,
              );
              return SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: grouped.entries.map((entry) {
                    final row = entry.value;
                    final current = row.values['current_budget'] ?? Money.zero;
                    final executed = row.values['executed'] ?? Money.zero;
                    // Convert only the integer ratio to pixels; never money to a double.
                    double pixels(Money value) =>
                        (value.cents.abs() * 10000 ~/ maxCents) /
                        10000 *
                        (height - 85);
                    return Semantics(
                      label:
                          '${entry.key}: presupuesto ${current.currency}, ejecutado ${executed.currency}',
                      button: onSelect != null,
                      child: SizedBox(
                        width: width,
                        child: InkWell(
                          borderRadius: BorderRadius.circular(10),
                          onTap: onSelect == null ? null : () => onSelect!(row),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.end,
                              children: [
                                FittedBox(
                                  child: Text(
                                    executed.currency,
                                    style: const TextStyle(
                                      fontSize: 10,
                                      color: ExbColors.secondaryText,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 12),
                                SizedBox(
                                  height: height - 85,
                                  child: Align(
                                    alignment: Alignment.bottomCenter,
                                    child: Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      crossAxisAlignment:
                                          CrossAxisAlignment.end,
                                      children: [
                                        CustomPaint(
                                          size: Size(32, pixels(current)),
                                          painter: BookStackPainter(
                                            ExbColors.books,
                                          ),
                                        ),
                                        const SizedBox(width: 6),
                                        CustomPaint(
                                          size: Size(32, pixels(executed)),
                                          painter: BookStackPainter(
                                            ExbColors.execution,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                                Container(height: 2, color: ExbColors.line),
                                const SizedBox(height: 10),
                                SizedBox(
                                  height: 42,
                                  child: Text(
                                    entry.key,
                                    textAlign: TextAlign.center,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontSize: 11),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'La altura de cada pila es proporcional al importe.',
          style: TextStyle(color: ExbColors.secondaryText, fontSize: 10),
        ),
      ],
    );
  }
}

class BookStackPainter extends CustomPainter {
  const BookStackPainter(this.color);
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    if (size.height <= 0) return;
    final shape = RRect.fromRectAndRadius(
      Offset.zero & size,
      const Radius.circular(3),
    );
    canvas.save();
    canvas.clipRRect(shape);
    canvas.drawRect(Offset.zero & size, Paint()..color = color);
    for (double y = size.height; y > 0; y -= 12) {
      canvas.drawLine(
        Offset(0, y),
        Offset(size.width, y),
        Paint()
          ..color = ExbColors.background
          ..strokeWidth = 2,
      );
      canvas.drawLine(
        Offset(9, y - 5),
        Offset(size.width - 4, y - 5),
        Paint()
          ..color = Colors.white.withValues(alpha: 0.45)
          ..strokeWidth = 1,
      );
    }
    canvas.drawRect(
      Rect.fromLTWH(0, 0, 4, size.height),
      Paint()..color = ExbColors.dark.withValues(alpha: 0.15),
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(BookStackPainter oldDelegate) =>
      color != oldDelegate.color;
}

class Legend extends StatelessWidget {
  const Legend({super.key, required this.color, required this.label});
  final Color color;
  final String label;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
      const SizedBox(width: 6),
      Text(
        label,
        style: const TextStyle(fontSize: 11, color: ExbColors.secondaryText),
      ),
    ],
  );
}

const fieldLabels = {
  'rubro': 'Rubro',
  'cuenta': 'Cuenta',
  'financier': 'Financiador',
  'region': 'Región',
  'area': 'Área',
  'month': 'Mes',
  'date': 'Fecha',
  'reference': 'Comprobante',
  'description': 'Concepto',
  'year': 'Gestión',
  'current_budget': 'Presupuesto',
  'initial_budget': 'Inicial',
  'modifications': 'Modificaciones',
  'executed': 'Ejecutado',
  'balance': 'Saldo',
  'execution_percentage': '% Ejecución',
  'difference': 'Diferencia',
  'difference_percentage': 'Variación %',
};

class ReportTable extends StatefulWidget {
  const ReportTable({
    super.key,
    required this.report,
    this.onAccount,
    this.onPage,
  });
  final FinancialReport report;
  final void Function(int)? onAccount;
  final void Function(int)? onPage;
  @override
  State<ReportTable> createState() => _ReportTableState();
}

class _ReportTableState extends State<ReportTable> {
  String? sortKey;
  int? sortColumn;
  bool ascending = true;
  int page = 0;
  @override
  void didUpdateWidget(ReportTable oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.report != widget.report) page = 0;
  }

  @override
  Widget build(BuildContext context) {
    final report = widget.report;
    if (report.rows.isEmpty) {
      return const MessageState(
        title: 'No encontramos registros.',
        detail: 'Prueba otro período o limpia los filtros.',
      );
    }
    final labels = report.rows.first.labels.keys.toList();
    final values = report.type == 'movements'
        ? ['executed']
        : [
            'current_budget',
            'executed',
            'balance',
            'execution_percentage',
            if (report.type == 'compare') 'difference',
            if (report.type == 'compare') 'difference_percentage',
          ];
    final keys = [...labels, ...values];
    final rows = [...report.rows];
    if (sortKey != null) {
      rows.sort((a, b) {
        final comparison = values.contains(sortKey)
            ? (a.values[sortKey] ?? Money.zero).compareTo(
                b.values[sortKey] ?? Money.zero,
              )
            : (a.labels[sortKey] ?? '').compareTo(b.labels[sortKey] ?? '');
        return ascending ? comparison : -comparison;
      });
    }
    final serverPaged = report.type == 'movements';
    final offset = serverPaged ? 0 : page * 10;
    final visible = serverPaged ? rows : rows.skip(offset).take(10).toList();
    final currentPage = serverPaged
        ? report.metadata['page'] as int? ?? 1
        : page + 1;
    final pageSize = serverPaged
        ? report.metadata['page_size'] as int? ?? 20
        : 10;
    final pages = (report.count / pageSize).ceil();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columnSpacing: 26,
            horizontalMargin: 8,
            headingRowHeight: 46,
            dataRowMinHeight: 54,
            dataRowMaxHeight: 74,
            headingRowColor: const WidgetStatePropertyAll(ExbColors.background),
            sortAscending: ascending,
            sortColumnIndex: sortColumn,
            columns: keys
                .map(
                  (key) => DataColumn(
                    label: Text(
                      fieldLabels[key] ?? key,
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 12,
                      ),
                    ),
                    numeric: values.contains(key),
                    onSort: (index, asc) => setState(() {
                      sortColumn = index;
                      sortKey = key;
                      ascending = asc;
                    }),
                  ),
                )
                .toList(),
            rows: visible
                .map(
                  (row) => DataRow(
                    cells: keys.map((key) {
                      final isNumber = values.contains(key);
                      final value = isNumber ? row.values[key] : null;
                      final text = isNumber
                          ? (value == null
                                ? '—'
                                : key.contains('percentage')
                                ? '${value.formatted} %'
                                : key == 'difference' &&
                                      (report.metadata['filters']
                                              as Json?)?['metric'] ==
                                          'execution_percentage'
                                ? '${value.formatted} pp'
                                : value.currency)
                          : row.labels[key] ?? '—';
                      return DataCell(
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 250),
                          child: Text(
                            text,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 12,
                              color: key == 'balance' && (value?.cents ?? 0) < 0
                                  ? ExbColors.amber
                                  : ExbColors.dark,
                            ),
                          ),
                        ),
                        onTap: () => _detail(row),
                      );
                    }).toList(),
                  ),
                )
                .toList(),
          ),
        ),
        const Divider(height: 24),
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: 20,
          children: [
            Text(
              '${report.count} registros · Página $currentPage de $pages',
              style: const TextStyle(
                fontSize: 12,
                color: ExbColors.secondaryText,
              ),
            ),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                IconButton(
                  tooltip: 'Página anterior',
                  onPressed: currentPage <= 1
                      ? null
                      : () {
                          if (serverPaged) {
                            widget.onPage?.call(currentPage - 1);
                          } else {
                            setState(() => page--);
                          }
                        },
                  icon: const Icon(Icons.chevron_left),
                ),
                IconButton(
                  tooltip: 'Página siguiente',
                  onPressed: currentPage >= pages
                      ? null
                      : () {
                          if (serverPaged) {
                            widget.onPage?.call(currentPage + 1);
                          } else {
                            setState(() => page++);
                          }
                        },
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ],
        ),
      ],
    );
  }

  void _detail(FinancialRow row) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Detalle de la consulta'),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final entry in row.labels.entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: SelectableText(
                      '${fieldLabels[entry.key] ?? entry.key}: ${entry.value}',
                    ),
                  ),
                for (final entry in row.values.entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      '${fieldLabels[entry.key] ?? entry.key}: ${entry.key.contains('percentage') ? '${entry.value.formatted} %' : entry.value.currency}',
                    ),
                  ),
                if (row.details['source_row'] != null)
                  Text('Origen: hoja BD, fila ${row.details['source_row']}'),
                if (row.details['original'] is Map)
                  ExpansionTile(
                    title: const Text('Campos originales de BD'),
                    children: [
                      for (final entry
                          in (row.details['original'] as Json).entries)
                        ListTile(
                          dense: true,
                          title: Text(entry.key),
                          subtitle: SelectableText('${entry.value ?? '—'}'),
                        ),
                    ],
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cerrar'),
          ),
          if (row.dimensions['cuenta'] != null && widget.onAccount != null)
            FilledButton(
              onPressed: () {
                Navigator.pop(context);
                widget.onAccount!(row.dimensions['cuenta']!);
              },
              child: const Text('Ver movimientos'),
            ),
        ],
      ),
    );
  }
}
