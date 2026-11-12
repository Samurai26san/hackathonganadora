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
import '../../shared/widgets/juku_mascot.dart';
import 'juku_text.dart';

const _monthNames = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
];

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
      color: ExbColors.paper,
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
                Expanded(
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
                  const Center(child: JukuMascot(JukuPose.saludo, size: 140)),
                  const SizedBox(height: 12),
                  const Text(
                    '¿Lo vemos juntos?',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Pídeme reportes mensuales, trimestrales o anuales, o pregúntame por saldos, financiadores y regiones.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: ExbColors.secondaryText,
                      height: 1.6,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 22),
                  for (final question in [
                    'Reporte anual de la gestión',
                    'Reporte del último mes',
                    '¿Cuánto presupuesto queda disponible?',
                    'Muéstrame la ejecución por financiador',
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
                  if (message.text.isNotEmpty) _bubble(message),
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
                          JukuMascot(
                            state.status.contains('motor')
                                ? JukuPose.corriendo
                                : JukuPose.pensando,
                            size: 52,
                            decorative: true,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              state.status,
                              style: TextStyle(
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
                      child: Row(
                        children: [
                          const JukuMascot(
                            JukuPose.pensando,
                            size: 48,
                            decorative: true,
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              state.error!,
                              style: TextStyle(
                                color: ExbColors.amber,
                                height: 1.6,
                                fontSize: 12,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const Divider(height: 1),
          _quickActions(state.busy),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 4, 14, 14),
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
          Padding(
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
                    style: TextStyle(
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

  Widget _bubble(JukuMessage message) {
    final user = message.role == 'user';
    final bubble = Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: user ? ExbColors.primaryFill : ExbColors.background,
        border: user ? null : Border.all(color: ExbColors.line),
        borderRadius: BorderRadius.only(
          topLeft: const Radius.circular(14),
          topRight: const Radius.circular(14),
          bottomLeft: Radius.circular(user ? 14 : 4),
          bottomRight: Radius.circular(user ? 4 : 14),
        ),
      ),
      child: user
          ? SelectableText(
              message.text,
              style: TextStyle(
                fontSize: 13,
                height: 1.5,
                color: ExbColors.onPrimaryFill,
              ),
            )
          : JukuText(message.text),
    );
    if (user) {
      return Align(
        alignment: Alignment.centerRight,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 320),
          child: bubble,
        ),
      );
    }
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(right: 8, top: 2),
          child: CircleAvatar(
            radius: 15,
            backgroundColor: ExbColors.story,
            child: SvgPicture.asset('assets/icons/juku.svg', height: 22),
          ),
        ),
        Expanded(
          child: message.pdfRequest == null
              ? bubble
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    bubble,
                    _PdfActions(request: message.pdfRequest!),
                  ],
                ),
        ),
      ],
    );
  }

  Widget _quickActions(bool busy) {
    Widget chip(String label, IconData icon, VoidCallback? onTap) => Padding(
      padding: const EdgeInsets.only(right: 6),
      child: ActionChip(
        avatar: Icon(icon, size: 15, color: ExbColors.green),
        label: Text(label, style: const TextStyle(fontSize: 11)),
        visualDensity: VisualDensity.compact,
        onPressed: busy ? null : onTap,
      ),
    );
    Widget menu<T>(
      String label,
      IconData icon,
      List<(T, String)> options,
      String Function(T) prompt,
    ) => Padding(
      padding: const EdgeInsets.only(right: 6),
      child: PopupMenuButton<T>(
        enabled: !busy,
        tooltip: label,
        onSelected: (value) => send(prompt(value)),
        itemBuilder: (_) => [
          for (final (value, text) in options)
            PopupMenuItem(value: value, height: 38, child: Text(text)),
        ],
        // Match the disabled look of the ActionChips while Juku responds.
        child: Opacity(
          opacity: busy ? 0.45 : 1,
          child: Chip(
            avatar: Icon(icon, size: 15, color: ExbColors.green),
            label: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(label, style: const TextStyle(fontSize: 11)),
                const Icon(Icons.arrow_drop_down, size: 16),
              ],
            ),
            visualDensity: VisualDensity.compact,
          ),
        ),
      ),
    );
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
      child: Row(
        children: [
          chip(
            'Reporte anual',
            Icons.calendar_month_outlined,
            () => send('Reporte anual de la gestión'),
          ),
          menu<int>(
            'Mensual',
            Icons.event_note_outlined,
            [for (var i = 0; i < 12; i++) (i + 1, _monthNames[i])],
            (month) =>
                'Reporte mensual de ${_monthNames[month - 1].toLowerCase()}',
          ),
          menu<int>('Trimestral', Icons.view_week_outlined, [
            for (var q = 1; q <= 4; q++) (q, '$q.º trimestre'),
          ], (quarter) => 'Reporte del trimestre Q$quarter'),
          chip(
            'Saldo',
            Icons.account_balance_wallet_outlined,
            () => send('¿Cuánto saldo queda disponible?'),
          ),
          chip('Ayuda', Icons.help_outline, () => send('ayuda')),
        ],
      ),
    );
  }

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

/// "PDF" downloads; "Compartir" opens WhatsApp, correo… where supported.
class _PdfActions extends ConsumerStatefulWidget {
  const _PdfActions({required this.request});
  final Json request;
  @override
  ConsumerState<_PdfActions> createState() => _PdfActionsState();
}

class _PdfActionsState extends ConsumerState<_PdfActions> {
  bool busy = false;

  Future<void> _run({required bool share}) async {
    setState(() => busy = true);
    final messenger = ScaffoldMessenger.of(context);
    try {
      final shared = await ref
          .read(apiProvider)
          .shareJukuPdf(widget.request, share: share);
      if (!shared) {
        messenger.showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const JukuMascot(JukuPose.pdf, size: 40, decorative: true),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    share
                        ? 'Este navegador no permite compartir archivos: se descargó el PDF para que lo adjuntes en WhatsApp o correo.'
                        : '¡Listo! Se descargó el reporte en PDF.',
                  ),
                ),
              ],
            ),
          ),
        );
      }
    } catch (error) {
      messenger.showSnackBar(SnackBar(content: Text('$error')));
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 2, bottom: 14),
    child: Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        FilledButton.tonalIcon(
          onPressed: busy ? null : () => _run(share: false),
          icon: busy
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.picture_as_pdf_outlined, size: 17),
          label: const Text('Descargar PDF', style: TextStyle(fontSize: 12)),
        ),
        OutlinedButton.icon(
          onPressed: busy ? null : () => _run(share: true),
          icon: const Icon(Icons.share_outlined, size: 17),
          label: const Text('Compartir', style: TextStyle(fontSize: 12)),
        ),
      ],
    ),
  );
}
