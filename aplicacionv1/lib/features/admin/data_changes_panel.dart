import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../dashboard/providers.dart';

final financialAdminProvider = FutureProvider.autoDispose.family<Json, String>(
  (ref, path) async => await ref.read(apiProvider).get(path) as Json,
);

class DataChangesPanel extends ConsumerStatefulWidget {
  const DataChangesPanel({super.key, this.history = false});
  final bool history;
  @override
  ConsumerState<DataChangesPanel> createState() => _DataChangesPanelState();
}

class _DataChangesPanelState extends ConsumerState<DataChangesPanel> {
  String kind = 'budget';
  int page = 1;
  bool busy = false;

  void refresh() {
    ref.invalidate(financialAdminProvider);
    ref.invalidate(reportProvider);
    ref.invalidate(catalogsProvider);
  }

  Future<void> perform(Future<void> Function() work) async {
    setState(() => busy = true);
    try {
      await work();
      refresh();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<String?> confirmation(String title) async {
    final reason = TextEditingController();
    bool confirmed = false;
    final result = await showDialog<String>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(title),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'La acción quedará registrada. El historial se conserva.',
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: reason,
                  maxLength: 1000,
                  maxLines: 3,
                  decoration: const InputDecoration(
                    labelText: 'Motivo obligatorio (mínimo 5 caracteres)',
                  ),
                  onChanged: (_) => update(() {}),
                ),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Confirmo esta operación'),
                  value: confirmed,
                  onChanged: (value) =>
                      update(() => confirmed = value ?? false),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: confirmed && reason.text.trim().length >= 5
                  ? () => Navigator.pop(dialogContext, reason.text.trim())
                  : null,
              child: const Text('Confirmar'),
            ),
          ],
        ),
      ),
    );
    reason.dispose();
    return result;
  }

  Future<void> edit([Json? current]) async {
    final raw = await ref.read(apiProvider).get('data/catalogs') as Json;
    if (!mounted) return;
    final catalogs = Catalogs(raw);
    if (catalogs.years.isEmpty ||
        [
          'region',
          'area',
          'financier',
          'rubro',
          'cuenta',
        ].any((k) => catalogs.items(k).isEmpty)) {
      throw const ApiError(
        'No hay categorías autorizadas suficientes para crear registros.',
      );
    }
    final filters = ref.read(filtersProvider);
    int selected(String key, int? initial) {
      final entries = catalogs.items(key);
      return entries.any((item) => item.id == initial)
          ? initial!
          : entries.first.id;
    }

    int year =
        (current?['year'] as int?) ??
        (catalogs.years.contains(filters.year)
            ? filters.year
            : catalogs.years.first);
    int month =
        (current?['month'] as int?) ??
        filters.month ??
        (kind == 'budget' ? 0 : DateTime.now().month);
    int region = selected(
      'region',
      current?['region_id'] as int? ?? filters.region,
    );
    int area = selected('area', current?['area_id'] as int? ?? filters.area);
    int financier = selected(
      'financier',
      current?['financier_id'] as int? ?? filters.financier,
    );
    int rubro = selected(
      'rubro',
      current?['rubro_id'] as int? ?? filters.rubro,
    );
    int? account = current?['cuenta_id'] as int? ?? filters.account;
    if (!catalogs
        .items('cuenta')
        .any((item) => item.parent == rubro && item.id == account)) {
      account = catalogs
          .items('cuenta')
          .where((item) => item.parent == rubro)
          .firstOrNull
          ?.id;
    }
    final amount = TextEditingController(
      text: current?['amount']?.toString() ?? '',
    );
    final date = TextEditingController(
      text:
          current?['date']?.toString() ??
          '$year-${month.clamp(1, 12).toString().padLeft(2, '0')}-01',
    );
    final reference = TextEditingController(
      text: current?['reference']?.toString() ?? '',
    );
    final description = TextEditingController(
      text: current?['description']?.toString() ?? '',
    );
    final reason = TextEditingController();
    final form = GlobalKey<FormState>();
    final body = await showDialog<Json>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, update) {
          Widget category(
            String label,
            String key,
            int? value,
            void Function(int) change, {
            List<CatalogItem>? options,
          }) => Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: DropdownButtonFormField<int>(
              key: ValueKey('$key-$value'),
              initialValue: value,
              isExpanded: true,
              decoration: InputDecoration(labelText: label),
              items: (options ?? catalogs.items(key))
                  .map(
                    (item) => DropdownMenuItem(
                      value: item.id,
                      child: Text(item.name, overflow: TextOverflow.ellipsis),
                    ),
                  )
                  .toList(),
              onChanged: (id) {
                if (id != null) update(() => change(id));
              },
              validator: (id) => id == null ? 'Selecciona una categoría' : null,
            ),
          );
          return AlertDialog(
            title: Text(
              '${current == null ? 'Añadir' : 'Editar'} ${kind == 'budget' ? 'presupuesto' : 'movimiento'}',
            ),
            content: SizedBox(
              width: 600,
              child: SingleChildScrollView(
                child: Form(
                  key: form,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      DropdownButtonFormField<int>(
                        initialValue: year,
                        decoration: const InputDecoration(labelText: 'Gestión'),
                        items: catalogs.years
                            .map(
                              (value) => DropdownMenuItem(
                                value: value,
                                child: Text('$value'),
                              ),
                            )
                            .toList(),
                        onChanged: (value) => update(() => year = value!),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<int>(
                        initialValue: month,
                        decoration: const InputDecoration(
                          labelText: 'Mes BD (0 = PTTO)',
                        ),
                        items: List.generate(
                          13,
                          (i) => DropdownMenuItem(
                            value: i,
                            child: Text(i == 0 ? 'PTTO' : '$i'),
                          ),
                        ),
                        onChanged: (value) => update(() => month = value!),
                      ),
                      const SizedBox(height: 12),
                      category('Región', 'region', region, (id) => region = id),
                      category('Área', 'area', area, (id) => area = id),
                      category(
                        'Financiador',
                        'financier',
                        financier,
                        (id) => financier = id,
                      ),
                      category('Rubro', 'rubro', rubro, (id) {
                        rubro = id;
                        account = null;
                      }),
                      category(
                        'Cuenta',
                        'cuenta',
                        account,
                        (id) => account = id,
                        options: catalogs
                            .items('cuenta')
                            .where((item) => item.parent == rubro)
                            .toList(),
                      ),
                      TextFormField(
                        controller: amount,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                          signed: true,
                        ),
                        decoration: const InputDecoration(
                          labelText: 'Importe en Bs',
                          helperText:
                              'Ejemplo: 1250,50. Sin separador de miles.',
                        ),
                        validator: (value) =>
                            RegExp(
                              r'^-?\d{1,18}([.,]\d{1,2})?$',
                            ).hasMatch((value ?? '').trim())
                            ? null
                            : 'Introduce un importe con hasta dos decimales',
                      ),
                      if (kind == 'movement') ...[
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: date,
                          decoration: const InputDecoration(
                            labelText: 'Fecha (AAAA-MM-DD)',
                          ),
                          validator: (value) =>
                              DateTime.tryParse(value ?? '') == null
                              ? 'Fecha inválida'
                              : null,
                        ),
                        const SizedBox(height: 12),
                        TextFormField(
                          controller: reference,
                          maxLength: 255,
                          decoration: const InputDecoration(
                            labelText: 'Comprobante / referencia',
                          ),
                        ),
                        TextFormField(
                          controller: description,
                          maxLength: 4000,
                          maxLines: 3,
                          decoration: const InputDecoration(
                            labelText: 'Descripción / glosa',
                          ),
                        ),
                      ],
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: reason,
                        maxLength: 1000,
                        maxLines: 3,
                        decoration: const InputDecoration(
                          labelText: 'Motivo obligatorio',
                        ),
                        validator: (value) => (value ?? '').trim().length < 5
                            ? 'Explica el motivo (mínimo 5 caracteres)'
                            : null,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext),
                child: const Text('Cancelar'),
              ),
              FilledButton(
                onPressed: () {
                  if (!form.currentState!.validate()) return;
                  Navigator.pop(dialogContext, <String, dynamic>{
                    'year': year,
                    'month': month,
                    'region_id': region,
                    'area_id': area,
                    'financier_id': financier,
                    'rubro_id': rubro,
                    'cuenta_id': account,
                    'amount': amount.text.trim().replaceAll(',', '.'),
                    'reason': reason.text.trim(),
                    if (kind == 'movement') 'date': date.text.trim(),
                    'reference': reference.text.trim(),
                    'description': description.text.trim(),
                    if (current != null) 'expected_version': current['version'],
                  });
                },
                child: const Text('Guardar cambio'),
              ),
            ],
          );
        },
      ),
    );
    for (final controller in [amount, date, reference, description, reason]) {
      controller.dispose();
    }
    if (body == null) return;
    final api = ref.read(apiProvider);
    if (current == null) {
      await api.post('data/records/$kind', data: body);
    } else {
      await api.put('data/records/$kind/${current['id']}', data: body);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (ref.watch(authProvider).valueOrNull?.isAdmin != true) {
      return const MessageState(
        title: 'Acceso reservado',
        detail:
            'Solo administración puede modificar datos y consultar su historial.',
      );
    }
    ref.listen(financialRevisionProvider, (previous, next) {
      if (previous?.valueOrNull != null &&
          next.valueOrNull != null &&
          previous!.valueOrNull != next.valueOrNull) {
        ref.invalidate(financialAdminProvider);
      }
    });
    final filters = ref.watch(filtersProvider);
    final path = widget.history
        ? 'data/history?page=$page'
        : Uri(
            path: 'data/records',
            queryParameters: {
              ...filters.toQuery().map(
                (key, value) => MapEntry(key, value.toString()),
              ),
              'kind': kind,
              'page': '$page',
              'page_size': '20',
            },
          ).toString();
    final state = ref.watch(financialAdminProvider(path));
    return Panel(
      title: widget.history ? 'Historial de datos' : 'Control de cambios',
      subtitle: widget.history
          ? 'Administrador, fecha, motivo y valores anteriores/nuevos. El historial se conserva al restaurar.'
          : 'Cambios compartidos entre dispositivos. Se aplican la gestión y los filtros del panel. El Excel original se conserva.',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              if (!widget.history) ...[
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'budget', label: Text('Presupuesto')),
                    ButtonSegment(
                      value: 'movement',
                      label: Text('Movimientos'),
                    ),
                  ],
                  selected: {kind},
                  onSelectionChanged: busy
                      ? null
                      : (value) => setState(() {
                          kind = value.first;
                          page = 1;
                        }),
                ),
                FilledButton.icon(
                  onPressed: busy ? null : () => perform(() => edit()),
                  icon: const Icon(Icons.add),
                  label: const Text('Añadir registro'),
                ),
              ],
              if (widget.history)
                OutlinedButton.icon(
                  onPressed: busy
                      ? null
                      : () => perform(
                          () => ref
                              .read(apiProvider)
                              .downloadJson(
                                'data/history/export',
                                'exb-historial-datos.json',
                              ),
                        ),
                  icon: const Icon(Icons.download),
                  label: const Text('Descargar JSON'),
                ),
              OutlinedButton.icon(
                onPressed: busy ? null : refresh,
                icon: const Icon(Icons.refresh),
                label: const Text('Actualizar'),
              ),
            ],
          ),
          const SizedBox(height: 18),
          if (busy) const LinearProgressIndicator(),
          state.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (error, _) => MessageState(
              title: 'No se pudieron cargar los registros',
              detail: '$error',
              onRetry: refresh,
            ),
            data: (data) {
              final rows = (data['rows'] as List).cast<Json>();
              final total = data['total'] as int;
              final size = widget.history ? 30 : 20;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (widget.history)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.restore),
                        label: const Text('Restaurar datos originales'),
                        onPressed: busy
                            ? null
                            : () => perform(() async {
                                final reason = await confirmation(
                                  '¿Restaurar los datos originales?',
                                );
                                if (reason != null) {
                                  await ref
                                      .read(apiProvider)
                                      .post(
                                        'data/restore',
                                        data: {
                                          'reason': reason,
                                          'confirm': true,
                                          'expected_revision': data['revision'],
                                        },
                                      );
                                }
                              }),
                      ),
                    ),
                  if (rows.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(18),
                      child: Text('No hay registros para este alcance.'),
                    ),
                  for (final row in rows)
                    if (widget.history)
                      ExpansionTile(
                        title: Text(
                          '${{'create': 'Creación', 'edit': 'Edición', 'delete': 'Eliminación', 'restore': 'Restauración'}[row['action']] ?? row['action']} · ${row['kind']} ${row['record_id'] ?? ''}',
                        ),
                        subtitle: Text(
                          '${row['administrator']} · ${DateTime.parse(row['timestamp'] as String).toLocal().toString().split('.').first}\nMotivo: ${row['reason']}',
                        ),
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text('Valores anteriores'),
                                SelectableText(
                                  const JsonEncoder.withIndent(
                                    '  ',
                                  ).convert(row['before']),
                                ),
                                const SizedBox(height: 16),
                                const Text('Valores nuevos'),
                                SelectableText(
                                  const JsonEncoder.withIndent(
                                    '  ',
                                  ).convert(row['after']),
                                ),
                              ],
                            ),
                          ),
                        ],
                      )
                    else
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          '${row['account_name']} · Bs ${row['amount']}',
                        ),
                        subtitle: Text(
                          'Gestión ${row['year']} · Mes ${row['month']} · ${row['date'] ?? ''}\n${row['reference'] ?? ''} ${row['description'] ?? ''}',
                        ),
                        trailing: Wrap(
                          children: [
                            IconButton(
                              tooltip: 'Editar',
                              onPressed: busy
                                  ? null
                                  : () => perform(() => edit(row)),
                              icon: const Icon(Icons.edit_outlined),
                            ),
                            IconButton(
                              tooltip: 'Eliminar',
                              onPressed: busy
                                  ? null
                                  : () => perform(() async {
                                      final reason = await confirmation(
                                        '¿Eliminar este registro?',
                                      );
                                      if (reason != null) {
                                        await ref
                                            .read(apiProvider)
                                            .post(
                                              'data/records/$kind/${row['id']}/delete',
                                              data: {
                                                'reason': reason,
                                                'confirm': true,
                                                'expected_version':
                                                    row['version'],
                                              },
                                            );
                                      }
                                    }),
                              icon: const Icon(Icons.delete_outline),
                            ),
                          ],
                        ),
                      ),
                  const SizedBox(height: 12),
                  Wrap(
                    crossAxisAlignment: WrapCrossAlignment.center,
                    spacing: 12,
                    children: [
                      Text('$total registros · Página $page'),
                      TextButton(
                        onPressed: page > 1 && !busy
                            ? () => setState(() => page--)
                            : null,
                        child: const Text('Anterior'),
                      ),
                      TextButton(
                        onPressed: page * size < total && !busy
                            ? () => setState(() => page++)
                            : null,
                        child: const Text('Siguiente'),
                      ),
                    ],
                  ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}
