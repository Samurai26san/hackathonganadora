import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:go_router/go_router.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../dashboard/providers.dart';
import '../reports/report_screen.dart';
import 'chat_controller.dart';

class JukuPanel extends ConsumerStatefulWidget {
  const JukuPanel({super.key, required this.onClose});
  final VoidCallback onClose;
  @override
  ConsumerState<JukuPanel> createState() => _JukuPanelState();
}

class _JukuPanelState extends ConsumerState<JukuPanel> {
  final input = TextEditingController();
  final scroll = ScrollController();
  @override
  void dispose() {
    input.dispose();
    scroll.dispose();
    super.dispose();
  }

  void send([String? suggestion]) {
    final text = suggestion ?? input.text.trim();
    if (text.isEmpty || text.length > 4000) return;
    input.clear();
    ref.read(chatProvider.notifier).send(text, ref.read(filtersProvider));
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(chatProvider);
    ref.listen(
      chatProvider,
      (_, next) => WidgetsBinding.instance.addPostFrameCallback((_) {
        if (scroll.hasClients) scroll.jumpTo(scroll.position.maxScrollExtent);
      }),
    );
    return Material(
      color: Colors.white,
      elevation: 4,
      child: Column(
        children: [
          Container(
            color: ExbColors.story,
            padding: const EdgeInsets.fromLTRB(14, 12, 8, 12),
            child: Row(
              children: [
                SvgPicture.asset('assets/icons/juku.svg', height: 56),
                const SizedBox(width: 10),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'JUKU',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1,
                        ),
                      ),
                      Text(
                        'Asistente financiero ExB',
                        style: TextStyle(
                          fontSize: 11,
                          color: ExbColors.secondaryText,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Historial de conversaciones',
                  onPressed: _history,
                  icon: const Icon(Icons.history, size: 20),
                ),
                IconButton(
                  tooltip: 'Nueva conversación',
                  onPressed: state.busy
                      ? null
                      : () => ref.read(chatProvider.notifier).newSession(),
                  icon: const Icon(Icons.add_comment_outlined, size: 20),
                ),
                IconButton(
                  tooltip: 'Minimizar Juku',
                  onPressed: widget.onClose,
                  icon: const Icon(Icons.close, size: 20),
                ),
              ],
            ),
          ),
          if (state.context != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
              color: ExbColors.background,
              child: Wrap(
                spacing: 4,
                children: [
                  for (final entry in state.context!.entries.where(
                    (entry) =>
                        (entry.value is List &&
                            (entry.value as List).isNotEmpty) ||
                        (entry.key == 'search' && entry.value != ''),
                  ))
                    InputChip(
                      visualDensity: VisualDensity.compact,
                      label: Text(
                        '${entry.key == 'years' ? 'Gestión' : entry.key}: ${entry.value}',
                        style: const TextStyle(fontSize: 10),
                      ),
                      onDeleted: state.busy
                          ? null
                          : () => send(
                              'Quita el filtro ${entry.key}; conserva los demás filtros.',
                            ),
                    ),
                ],
              ),
            ),
          Expanded(
            child: ListView(
              controller: scroll,
              padding: const EdgeInsets.all(16),
              children: [
                if (state.messages.isEmpty) ...[
                  const SizedBox(height: 22),
                  Center(
                    child: SvgPicture.asset(
                      'assets/icons/juku.svg',
                      height: 100,
                    ),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    '¿Lo vemos juntos?',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    'Pregúntame sobre el presupuesto o busca evidencia en los documentos de la institución.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: ExbColors.secondaryText,
                      height: 1.6,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 22),
                  for (final question in [
                    '¿Cuánto presupuesto queda disponible?',
                    'Muéstrame la ejecución por financiador',
                    '¿Qué dice el manual institucional?',
                  ])
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: OutlinedButton(
                        onPressed: () => send(question),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(vertical: 10),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  question,
                                  style: const TextStyle(fontSize: 12),
                                ),
                              ),
                              const Icon(Icons.north_east, size: 15),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
                for (final message in state.messages) ...[
                  if (message.text.isNotEmpty)
                    Align(
                      alignment: message.role == 'user'
                          ? Alignment.centerRight
                          : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 14),
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: message.role == 'user'
                              ? ExbColors.story
                              : ExbColors.background,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: SelectableText(
                          message.text,
                          style: const TextStyle(fontSize: 13, height: 1.65),
                        ),
                      ),
                    ),
                  if (message.report != null)
                    _financialResult(message.report!, state.context),
                  if (message.citations.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 14),
                      child: ExpansionTile(
                        title: Text(
                          '${message.citations.length} fuentes institucionales',
                          style: const TextStyle(fontSize: 13),
                        ),
                        children: [
                          for (final citation in message.citations)
                            ListTile(
                              title: Text('${citation['source_title']}'),
                              subtitle: SelectableText(
                                '${citation['content']}',
                                style: const TextStyle(fontSize: 12),
                              ),
                            ),
                        ],
                      ),
                    ),
                ],
                if (state.busy)
                  Semantics(
                    liveRegion: true,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Row(
                        children: [
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              state.status,
                              style: const TextStyle(
                                fontSize: 12,
                                color: ExbColors.secondaryText,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                if (state.error != null)
                  Semantics(
                    liveRegion: true,
                    child: Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: ExbColors.background,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text(
                        state.error!,
                        style: const TextStyle(
                          color: ExbColors.amber,
                          height: 1.6,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const Divider(height: 1),
          Padding(
            padding: const EdgeInsets.all(14),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Expanded(
                  child: TextField(
                    controller: input,
                    enabled: !state.busy,
                    minLines: 1,
                    maxLines: 4,
                    maxLength: 4000,
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => send(),
                    decoration: const InputDecoration(
                      hintText: 'Pregúntale a Juku…',
                      counterText: '',
                      labelText: 'Tu consulta',
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  tooltip: 'Enviar consulta',
                  onPressed: state.busy ? null : () => send(),
                  icon: const Icon(Icons.arrow_upward),
                ),
              ],
            ),
          ),
          const Padding(
            padding: EdgeInsets.only(bottom: 12),
            child: Text(
              'Consulta de solo lectura · Cifras verificadas por el motor',
              style: TextStyle(fontSize: 10, color: ExbColors.secondaryText),
            ),
          ),
        ],
      ),
    );
  }

  Widget _financialResult(
    FinancialReport report,
    Json? activeContext,
  ) => Container(
    margin: const EdgeInsets.only(bottom: 16),
    padding: const EdgeInsets.all(14),
    decoration: BoxDecoration(
      border: Border.all(color: ExbColors.line),
      borderRadius: BorderRadius.circular(12),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          report.title,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: 14),
        for (final key in [
          'current_budget',
          'executed',
          'balance',
          'execution_percentage',
        ])
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    fieldLabels[key]!,
                    style: const TextStyle(
                      fontSize: 11,
                      color: ExbColors.secondaryText,
                    ),
                  ),
                ),
                Text(
                  key == 'execution_percentage'
                      ? '${report.summary[key]?.formatted} %'
                      : report.summary[key]?.currency ?? '—',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        const SizedBox(height: 10),
        BookChart(
          rows: report.rows.take(5).toList(),
          dimension:
              report.rows.firstOrNull?.labels.keys.firstOrNull ?? 'rubro',
          height: 180,
        ),
        const SizedBox(height: 12),
        for (final row in report.rows.take(3))
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              '${row.labels.values.join(' · ')}: ${row.values['executed']?.currency ?? '—'}',
              style: const TextStyle(fontSize: 11),
            ),
          ),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            FilledButton.tonal(
              onPressed: () {
                final savedFilters =
                    report.metadata['filters'] as Json? ?? activeContext;
                if (savedFilters != null) {
                  ref.read(filtersProvider.notifier).state =
                      BudgetFilters.fromContext(savedFilters);
                }
                if (report.type != 'compare') {
                  ref.read(selectedReportProvider.notifier).state = report.type;
                }
                context.go(
                  report.type == 'movements'
                      ? '/movimientos'
                      : report.type == 'compare'
                      ? '/gestiones'
                      : '/reportes',
                );
              },
              child: const Text('Ver detalle', style: TextStyle(fontSize: 12)),
            ),
            ExportButton(
              report: report.type,
              filters: report.metadata['filters'] is Json
                  ? BudgetFilters.fromContext(
                      report.metadata['filters'] as Json,
                    )
                  : null,
              compareYear: report.type == 'compare'
                  ? ((report.metadata['filters'] as Json)['years']
                                as List<dynamic>)
                            .last
                        as int
                  : null,
            ),
          ],
        ),
      ],
    ),
  );

  Future<void> _history() async {
    try {
      final rows = await ref.read(apiProvider).get('sessions') as List<dynamic>;
      if (!mounted) return;
      final id = await showDialog<String>(
        context: context,
        builder: (context) => SimpleDialog(
          title: const Text('Tus conversaciones'),
          children: [
            if (rows.isEmpty)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Text('Todavía no hay conversaciones guardadas.'),
              ),
            for (final dynamic row in rows)
              SimpleDialogOption(
                onPressed: () => Navigator.pop(context, row['id'] as String),
                child: Text(row['title'] as String),
              ),
          ],
        ),
      );
      if (id != null) await ref.read(chatProvider.notifier).loadSession(id);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }
}
