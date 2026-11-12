import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/auth/auth_controller.dart';
import '../dashboard/providers.dart';
import 'workspace_widgets.dart';

const curationFields = [
  'kind',
  'year',
  'month',
  'date',
  'region_id',
  'area_id',
  'financier_id',
  'rubro_id',
  'cuenta_id',
  'amount',
  'reference',
  'description',
];
const fieldNames = {
  'kind': 'Tipo',
  'year': 'Gestión',
  'month': 'Mes (0=PTTO)',
  'date': 'Fecha',
  'region_id': 'Región',
  'area_id': 'Área',
  'financier_id': 'Financiador',
  'rubro_id': 'Rubro',
  'cuenta_id': 'Cuenta',
  'amount': 'Importe BOB',
  'reference': 'Comprobante',
  'description': 'Descripción',
};

class CurationScreen extends ConsumerStatefulWidget {
  const CurationScreen({super.key});
  @override
  ConsumerState<CurationScreen> createState() => _CurationScreenState();
}

class _CurationScreenState extends ConsumerState<CurationScreen> {
  List<Json> batches = [], rows = [];
  Json catalogs = {};
  int? batch;
  int page = 1, total = 0;
  String? status, error;
  bool busy = false;
  ApiClient get api => ref.read(apiProvider);
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  Future<void> load() async {
    if (!mounted) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final bs = (await api.get('curation/batches') as List).cast<Json>();
      final cat = await api.get('curation/catalogs') as Json;
      batch ??= bs.isEmpty ? null : bs.first['id'] as int;
      final data = batch == null
          ? <String, dynamic>{'rows': [], 'total': 0}
          : await api.get(
                  'curation/batches/$batch',
                  query: {'page': page, if (status != null) 'status': status},
                )
                as Json;
      if (mounted)
        setState(() {
          batches = bs;
          catalogs = cat;
          rows = (data['rows'] as List).cast<Json>();
          total = data['total'] as int;
        });
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> act(Json row, String action) async {
    final reason = await askReason(
      context,
      action == 'validate'
          ? 'Validar manualmente esta fila'
          : action == 'consolidate'
          ? 'Incorporar esta fila a los datos compartidos'
          : 'Predecir etiquetas de la fila',
    );
    if (reason == null) return;
    setState(() => busy = true);
    try {
      await api.post(
        'curation/rows/${row['id']}/$action',
        data: {'version': row['version'], 'reason': reason},
      );
      if (action == 'consolidate') {
        ref.invalidate(reportProvider);
        ref.invalidate(catalogsProvider);
      }
      await load();
    } catch (e) {
      if (mounted) {
        setState(() => busy = false);
        showFailure(context, e);
      }
    }
  }

  Future<void> edit(Json? row, {bool prediction = false, String? focus}) async {
    final data = <String, dynamic>{
      if (row != null) ...row['data'] as Json,
      if (row == null) 'kind': 'movement',
      if (prediction)
        ...((row!['prediction'] as Json)['labels'] as Json? ?? {}),
    };
    final controllers = {
      for (final k in curationFields)
        k: TextEditingController(text: '${data[k] ?? ''}'),
    };
    final reason = TextEditingController();
    String? localError;
    final saved = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(
            row == null
                ? 'Nueva fila en preparación'
                : prediction
                ? 'Revisar etiquetas sugeridas'
                : 'Corregir fila ${row['source_row']}',
          ),
          content: SizedBox(
            width: 650,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Los cambios quedan en preparación. Valida la fila y consolídala para actualizar los reportes.',
                  ),
                  const SizedBox(height: 12),
                  for (final k in curationFields)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child:
                          catalogs.containsKey(
                            {
                              'region_id': 'regiones',
                              'area_id': 'areas',
                              'financier_id': 'financiadores',
                              'rubro_id': 'rubros',
                              'cuenta_id': 'cuentas',
                            }[k],
                          )
                          ? DropdownButtonFormField<String>(
                              key: ValueKey(
                                '$k-${controllers['rubro_id']!.text}',
                              ),
                              initialValue:
                                  (catalogs[{
                                            'region_id': 'regiones',
                                            'area_id': 'areas',
                                            'financier_id': 'financiadores',
                                            'rubro_id': 'rubros',
                                            'cuenta_id': 'cuentas',
                                          }[k]]
                                          as List)
                                      .any(
                                        (dynamic c) =>
                                            '${c['id']}' ==
                                                controllers[k]!.text &&
                                            (k != 'cuenta_id' ||
                                                '${c['rubro_id']}' ==
                                                    controllers['rubro_id']!
                                                        .text),
                                      )
                                  ? controllers[k]!.text
                                  : null,
                              isExpanded: true,
                              decoration: InputDecoration(
                                labelText: fieldNames[k],
                              ),
                              items: [
                                for (final c
                                    in catalogs[{
                                          'region_id': 'regiones',
                                          'area_id': 'areas',
                                          'financier_id': 'financiadores',
                                          'rubro_id': 'rubros',
                                          'cuenta_id': 'cuentas',
                                        }[k]]
                                        as List)
                                  if (k != 'cuenta_id' ||
                                      '${c['rubro_id']}' ==
                                          controllers['rubro_id']!.text)
                                    DropdownMenuItem(
                                      value: '${c['id']}',
                                      child: Text(
                                        '${c['name']}',
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                              ],
                              onChanged: (v) => update(() {
                                controllers[k]!.text = v ?? '';
                                if (k == 'rubro_id')
                                  controllers['cuenta_id']!.clear();
                              }),
                            )
                          : TextField(
                              controller: controllers[k],
                              autofocus: k == focus,
                              maxLines: k == 'description' ? 3 : 1,
                              decoration: InputDecoration(
                                labelText: fieldNames[k],
                                helperText: k == 'kind'
                                    ? 'budget = presupuesto · movement = movimiento'
                                    : k == 'date'
                                    ? 'AAAA-MM-DD o DD/MM/AAAA'
                                    : null,
                              ),
                            ),
                    ),
                  TextField(
                    controller: reason,
                    decoration: const InputDecoration(
                      labelText: 'Motivo obligatorio (mínimo 5 caracteres)',
                    ),
                  ),
                  if (localError != null)
                    Text(
                      localError!,
                      style: const TextStyle(color: Colors.red),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () async {
                if (reason.text.trim().length < 5) {
                  update(
                    () => localError =
                        'Indica un motivo de al menos cinco caracteres.',
                  );
                  return;
                }
                final values = <String, dynamic>{
                  for (final k in curationFields)
                    if (controllers[k]!.text.trim().isNotEmpty)
                      k: controllers[k]!.text.trim(),
                };
                try {
                  if (row == null) {
                    final created =
                        await api.post(
                              'curation/batches',
                              data: {
                                'filename': 'Registro manual',
                                'reason': reason.text.trim(),
                                'rows': [values],
                              },
                            )
                            as Json;
                    batch = created['id'] as int;
                    page = 1;
                  } else {
                    await api.put(
                      'curation/rows/${row['id']}',
                      data: {
                        'data': values,
                        'version': row['version'],
                        'reason': reason.text.trim(),
                      },
                    );
                  }
                  if (context.mounted) Navigator.pop(context, true);
                } catch (e) {
                  update(() => localError = '$e');
                }
              },
              child: const Text('Guardar en preparación'),
            ),
          ],
        ),
      ),
    );
    for (final c in controllers.values) {
      c.dispose();
    }
    reason.dispose();
    if (saved == true) await load();
  }

  String label(String k, dynamic value) {
    final category = {
      'region_id': 'regiones',
      'area_id': 'areas',
      'financier_id': 'financiadores',
      'rubro_id': 'rubros',
      'cuenta_id': 'cuentas',
    }[k];
    for (final c in catalogs[category] as List? ?? []) {
      if ('${c['id']}' == '$value') return '${c['name']}';
    }
    return '${value ?? '—'}';
  }

  @override
  Widget build(BuildContext context) {
    final role = ref.watch(authProvider).valueOrNull?.role;
    if (!['admin', 'analyst', 'technician'].contains(role))
      return const Text('Espacio reservado para técnicos y administradores.');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Prepara el Excel sin alterar el original. Corrige celdas, revisa sugerencias y valida cada fila antes de consolidar.',
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            FilledButton.icon(
              onPressed: busy
                  ? null
                  : () async {
                      try {
                        final created = await api.uploadCurationWorkbook();
                        if (created != null) {
                          batch = created['id'] as int;
                          page = 1;
                          await load();
                        }
                      } catch (e) {
                        if (context.mounted) showFailure(context, e);
                      }
                    },
              icon: const Icon(Icons.upload_file),
              label: const Text('Cargar Excel de preparación'),
            ),
            OutlinedButton.icon(
              onPressed: busy ? null : () => edit(null),
              icon: const Icon(Icons.add),
              label: const Text('Nueva fila'),
            ),
            OutlinedButton(
              onPressed: () => api
                  .downloadDocument(
                    'curation/template',
                    {},
                    'plantilla-curaduria.xlsx',
                  )
                  .catchError((Object e) {
                    if (context.mounted) showFailure(context, e);
                  }),
              child: const Text('Descargar plantilla'),
            ),
            IconButton(
              onPressed: busy ? null : load,
              tooltip: 'Actualizar',
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        const SizedBox(height: 16),
        Wrap(
          spacing: 16,
          runSpacing: 12,
          children: [
            SizedBox(
              width: 280,
              child: DropdownButtonFormField<int>(
                key: ValueKey(batch),
                initialValue: batch,
                isExpanded: true,
                decoration: const InputDecoration(
                  labelText: 'Lote de trabajo privado',
                ),
                items: [
                  for (final b in batches)
                    DropdownMenuItem(
                      value: b['id'] as int,
                      child: Text(
                        '#${b['id']} · ${b['filename']}',
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                ],
                onChanged: busy
                    ? null
                    : (v) {
                        batch = v;
                        page = 1;
                        load();
                      },
              ),
            ),
            SizedBox(
              width: 240,
              child: DropdownButtonFormField<String>(
                initialValue: status ?? '',
                decoration: const InputDecoration(
                  labelText: 'Estado de preparación',
                ),
                items: const [
                  DropdownMenuItem(value: '', child: Text('Todos')),
                  DropdownMenuItem(value: 'pending', child: Text('Pendiente')),
                  DropdownMenuItem(value: 'predicted', child: Text('Predicho')),
                  DropdownMenuItem(
                    value: 'validated',
                    child: Text('Validado manualmente'),
                  ),
                  DropdownMenuItem(
                    value: 'consolidated',
                    child: Text('Consolidado'),
                  ),
                ],
                onChanged: (v) {
                  status = v == '' ? null : v;
                  page = 1;
                  load();
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        if (busy) const LinearProgressIndicator(),
        if (error != null)
          Text(error!, style: const TextStyle(color: Colors.red)),
        if (rows.isEmpty && !busy)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Text('Carga la plantilla o añade una fila para comenzar.'),
          ),
        if (rows.isNotEmpty)
          Card(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columns: [
                  const DataColumn(label: Text('Fila / Estado')),
                  for (final k in curationFields)
                    DataColumn(label: Text(fieldNames[k]!)),
                  const DataColumn(label: Text('Hallazgos y acciones')),
                ],
                rows: [
                  for (final row in rows)
                    DataRow(
                      cells: [
                        DataCell(
                          SizedBox(
                            width: 170,
                            child: Text(
                              '#${row['source_row']} · ${statusLabel(row)}',
                            ),
                          ),
                        ),
                        for (final k in curationFields)
                          DataCell(
                            ConstrainedBox(
                              constraints: const BoxConstraints(maxWidth: 160),
                              child: Text(
                                label(k, (row['data'] as Json)[k]),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            onTap: busy || row['target_id'] != null
                                ? null
                                : () => edit(row, focus: k),
                          ),
                        DataCell(
                          SizedBox(
                            width: 520,
                            child: Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    (row['issues'] as List).join('; '),
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                                IconButton(
                                  tooltip: 'Ver bitácora de esta fila',
                                  onPressed: busy
                                      ? null
                                      : () async {
                                          try {
                                            final history = await api.get(
                                              'curation/rows/${row['id']}/history',
                                            );
                                            if (context.mounted)
                                              await showDialog<void>(
                                                context: context,
                                                builder: (context) => AlertDialog(
                                                  title: Text(
                                                    'Bitácora · Fila ${row['source_row']}',
                                                  ),
                                                  content: SizedBox(
                                                    width: 700,
                                                    child:
                                                        SingleChildScrollView(
                                                          child: ReportTree(
                                                            history,
                                                          ),
                                                        ),
                                                  ),
                                                  actions: [
                                                    TextButton(
                                                      onPressed: () =>
                                                          Navigator.pop(
                                                            context,
                                                          ),
                                                      child: const Text(
                                                        'Cerrar',
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              );
                                          } catch (e) {
                                            if (context.mounted)
                                              showFailure(context, e);
                                          }
                                        },
                                  icon: const Icon(Icons.history),
                                ),
                                if (row['target_id'] == null) ...[
                                  IconButton(
                                    tooltip: 'Editar fila',
                                    onPressed: busy ? null : () => edit(row),
                                    icon: const Icon(Icons.edit_outlined),
                                  ),
                                  IconButton(
                                    tooltip:
                                        'Predecir todas las etiquetas de la fila',
                                    onPressed: busy
                                        ? null
                                        : () => act(row, 'predict'),
                                    icon: const Icon(
                                      Icons.auto_awesome_outlined,
                                    ),
                                  ),
                                  if (((row['prediction'] as Json)['labels']
                                              as Map? ??
                                          {})
                                      .isNotEmpty)
                                    IconButton(
                                      tooltip: 'Revisar y aplicar sugerencias',
                                      onPressed: busy
                                          ? null
                                          : () => edit(row, prediction: true),
                                      icon: const Icon(
                                        Icons.playlist_add_check,
                                      ),
                                    ),
                                  IconButton(
                                    tooltip: 'Validar fila manualmente',
                                    onPressed: busy
                                        ? null
                                        : () => act(row, 'validate'),
                                    icon: const Icon(Icons.fact_check_outlined),
                                  ),
                                  if (row['status'] == 'validated')
                                    IconButton(
                                      tooltip:
                                          'Consolidar en reportes compartidos',
                                      onPressed: busy
                                          ? null
                                          : () => act(row, 'consolidate'),
                                      icon: const Icon(Icons.publish),
                                    ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
          ),
        Row(
          children: [
            Text('$total filas · Página $page'),
            const Spacer(),
            IconButton(
              onPressed: page > 1 && !busy
                  ? () {
                      page--;
                      load();
                    }
                  : null,
              icon: const Icon(Icons.chevron_left),
            ),
            IconButton(
              onPressed: page * 25 < total && !busy
                  ? () {
                      page++;
                      load();
                    }
                  : null,
              icon: const Icon(Icons.chevron_right),
            ),
          ],
        ),
        const Text(
          'Predicción supervisada por similitud con tus validaciones anteriores. El porcentaje es orientativo, no una probabilidad calibrada. Las sugerencias requieren revisión manual.',
        ),
      ],
    );
  }

  String statusLabel(Json row) => switch (row['status']) {
    'validated' => 'Validado manualmente',
    'consolidated' => 'Consolidado',
    'superseded' => 'Modificado posteriormente',
    'predicted' => 'Predicho · ${(row['prediction'] as Json)['confidence']} %',
    _ => 'Pendiente',
  };
}
