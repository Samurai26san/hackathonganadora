import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/auth/auth_controller.dart';
import 'workspace_widgets.dart';

class AccountingScreen extends ConsumerStatefulWidget {
  const AccountingScreen({super.key});
  @override
  ConsumerState<AccountingScreen> createState() => _AccountingScreenState();
}

class _AccountingScreenState extends ConsumerState<AccountingScreen> {
  Json catalogs = {}, statements = {};
  String? error;
  bool busy = false;
  final cutoff = TextEditingController(
    text: DateTime.now().toIso8601String().substring(0, 10),
  );
  ApiClient get api => ref.read(apiProvider);
  List<Json> get accounts => (catalogs['accounts'] as List? ?? []).cast<Json>();
  @override
  void initState() {
    super.initState();
    Future.microtask(load);
  }

  @override
  void dispose() {
    cutoff.dispose();
    super.dispose();
  }

  Future<void> load() async {
    setState(() {
      busy = true;
      error = null;
    });
    try {
      final c = await api.get('accounting/catalogs') as Json;
      final s =
          await api.get('accounting/statements', query: {'cutoff': cutoff.text})
              as Json;
      if (mounted)
        setState(() {
          catalogs = c;
          statements = s;
        });
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> form(String type) async {
    final fields = type == 'account'
        ? {
            'code': 'Código contable',
            'name': 'Nombre de la cuenta',
            'liquidity_order': 'Orden de liquidez',
          }
        : type == 'disclosure'
        ? {
            'year': 'Gestión',
            'title': 'Título',
            'body': 'Contenido cualitativo',
          }
        : {
            'date': 'Fecha AAAA-MM-DD',
            'reference': 'Comprobante único',
            'description': 'Descripción',
            'reason': 'Motivo obligatorio',
          };
    final cs = {
      for (final k in fields.keys)
        k: TextEditingController(
          text: k == 'year'
              ? '${DateTime.now().year}'
              : k == 'liquidity_order'
              ? '0'
              : k == 'date'
              ? cutoff.text
              : '',
        ),
    };
    String kind = type == 'account' ? 'asset' : 'auditor',
        section = 'cash',
        risk = 'none',
        entryType = 'normal',
        equityEvent = 'other';
    int? parent, noteAccount;
    bool cash = false, saving = false;
    String? issue;
    final lines = <Map<String, dynamic>>[
      {
        'account_id': null,
        'debit': TextEditingController(),
        'credit': TextEditingController(),
        'cash_activity': null,
      },
      {
        'account_id': null,
        'debit': TextEditingController(),
        'credit': TextEditingController(),
        'cash_activity': null,
      },
    ];
    await showDialog<void>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, update) => AlertDialog(
          title: Text(
            type == 'account'
                ? 'Añadir cuenta o subcuenta'
                : type == 'disclosure'
                ? 'Incorporar dictamen o nota'
                : 'Registrar asiento de partida doble',
          ),
          content: SizedBox(
            width: 760,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (type == 'entry')
                    const Text(
                      'Los asientos contabilizados se conservan. Para corregirlos, registra un contraasiento con referencia propia.',
                    ),
                  for (final entry in fields.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: TextField(
                        controller: cs[entry.key],
                        maxLines: entry.key == 'body'
                            ? 7
                            : entry.key == 'description'
                            ? 2
                            : 1,
                        decoration: InputDecoration(labelText: entry.value),
                      ),
                    ),
                  if (type == 'account') ...[
                    DropdownButtonFormField<String>(
                      initialValue: kind,
                      decoration: const InputDecoration(
                        labelText: 'Tipo de cuenta',
                      ),
                      items: [
                        for (final k in [
                          'asset',
                          'liability',
                          'equity',
                          'income',
                          'expense',
                          'contingent',
                          'order',
                        ])
                          DropdownMenuItem(
                            value: k,
                            child: Text(
                              {
                                'asset': 'Activo',
                                'liability': 'Pasivo',
                                'equity': 'Patrimonio',
                                'income': 'Ingreso',
                                'expense': 'Gasto',
                                'contingent': 'Contingente',
                                'order': 'Orden',
                              }[k]!,
                            ),
                          ),
                      ],
                      onChanged: (v) => update(() {
                        kind = v!;
                        section =
                            ((catalogs['sections'] as Json)[kind] as List).first
                                as String;
                        parent = null;
                        cash = false;
                      }),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      key: ValueKey(kind),
                      initialValue: section,
                      decoration: const InputDecoration(
                        labelText: 'Sección del estado financiero',
                      ),
                      items: [
                        for (final s
                            in (catalogs['sections'] as Json? ?? {})[kind]
                                    as List? ??
                                [])
                          DropdownMenuItem(value: '$s', child: Text('$s')),
                      ],
                      onChanged: (v) => update(() => section = v!),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      key: ValueKey('$kind-$section'),
                      initialValue: parent,
                      decoration: const InputDecoration(
                        labelText: 'Cuenta superior (opcional)',
                      ),
                      isExpanded: true,
                      items: [
                        const DropdownMenuItem<int>(
                          value: null,
                          child: Text('Sin cuenta superior'),
                        ),
                        for (final a in accounts)
                          if (a['kind'] == kind && a['section'] == section)
                            DropdownMenuItem(
                              value: a['id'] as int,
                              child: Text('${a['code']} · ${a['name']}'),
                            ),
                      ],
                      onChanged: (v) => update(() => parent = v),
                    ),
                    SwitchListTile(
                      title: const Text(
                        'Cuenta de disponibilidades / efectivo',
                      ),
                      value: cash,
                      onChanged: (v) => update(() => cash = v),
                    ),
                  ],
                  if (type == 'disclosure') ...[
                    DropdownButtonFormField<String>(
                      initialValue: kind,
                      decoration: const InputDecoration(labelText: 'Bloque'),
                      items: const [
                        DropdownMenuItem(
                          value: 'auditor',
                          child: Text('Dictamen del auditor independiente'),
                        ),
                        DropdownMenuItem(
                          value: 'note',
                          child: Text('Nota a los estados financieros'),
                        ),
                      ],
                      onChanged: (v) => update(() => kind = v!),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: risk,
                      decoration: const InputDecoration(
                        labelText: 'Alerta de riesgo',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'none',
                          child: Text('Sin alerta'),
                        ),
                        DropdownMenuItem(value: 'low', child: Text('Bajo')),
                        DropdownMenuItem(value: 'medium', child: Text('Medio')),
                        DropdownMenuItem(value: 'high', child: Text('Alto')),
                      ],
                      onChanged: (v) => update(() => risk = v!),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      initialValue: noteAccount,
                      isExpanded: true,
                      decoration: const InputDecoration(
                        labelText: 'Cuenta vinculada (opcional)',
                      ),
                      items: [
                        const DropdownMenuItem<int>(
                          value: null,
                          child: Text('Nota general'),
                        ),
                        for (final a in accounts)
                          DropdownMenuItem(
                            value: a['id'] as int,
                            child: Text('${a['code']} · ${a['name']}'),
                          ),
                      ],
                      onChanged: (v) => update(() => noteAccount = v),
                    ),
                  ],
                  if (type == 'entry') ...[
                    DropdownButtonFormField<String>(
                      initialValue: entryType,
                      decoration: const InputDecoration(
                        labelText: 'Tipo de asiento',
                      ),
                      items: const [
                        DropdownMenuItem(
                          value: 'normal',
                          child: Text('Movimiento'),
                        ),
                        DropdownMenuItem(
                          value: 'opening',
                          child: Text('Saldo de apertura'),
                        ),
                        DropdownMenuItem(
                          value: 'closing',
                          child: Text('Cierre de resultados'),
                        ),
                        DropdownMenuItem(
                          value: 'reversal',
                          child: Text('Contraasiento'),
                        ),
                      ],
                      onChanged: (v) => update(() => entryType = v!),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      initialValue: equityEvent,
                      decoration: const InputDecoration(
                        labelText: 'Movimiento patrimonial',
                      ),
                      items: [
                        for (final k in [
                          'opening',
                          'reinvestment',
                          'reserve',
                          'dividend',
                          'contribution',
                          'other',
                        ])
                          DropdownMenuItem(
                            value: k,
                            child: Text(
                              {
                                'opening': 'Saldo inicial',
                                'reinvestment': 'Reinversión de utilidades',
                                'reserve': 'Constitución de reservas',
                                'dividend': 'Distribución de dividendos',
                                'contribution': 'Aportes',
                                'other': 'Otros',
                              }[k]!,
                            ),
                          ),
                      ],
                      onChanged: (v) => update(() => equityEvent = v!),
                    ),
                    for (var i = 0; i < lines.length; i++)
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  Text('Línea ${i + 1}'),
                                  const Spacer(),
                                  if (lines.length > 2)
                                    IconButton(
                                      onPressed: () => update(() {
                                        final removed = lines.removeAt(i);
                                        (removed['debit']
                                                as TextEditingController)
                                            .dispose();
                                        (removed['credit']
                                                as TextEditingController)
                                            .dispose();
                                      }),
                                      tooltip: 'Quitar línea',
                                      icon: const Icon(
                                        Icons.remove_circle_outline,
                                      ),
                                    ),
                                ],
                              ),
                              DropdownButtonFormField<int>(
                                key: ValueKey(
                                  'line-$i-${lines[i]['account_id']}',
                                ),
                                initialValue: lines[i]['account_id'] as int?,
                                isExpanded: true,
                                decoration: const InputDecoration(
                                  labelText: 'Cuenta final',
                                ),
                                items: [
                                  for (final a in accounts)
                                    if (!accounts.any(
                                      (b) => b['parent_id'] == a['id'],
                                    ))
                                      DropdownMenuItem(
                                        value: a['id'] as int,
                                        child: Text(
                                          '${a['code']} · ${a['name']}',
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                ],
                                onChanged: (v) =>
                                    update(() => lines[i]['account_id'] = v),
                              ),
                              const SizedBox(height: 10),
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller:
                                          lines[i]['debit']
                                              as TextEditingController,
                                      decoration: const InputDecoration(
                                        labelText: 'Debe BOB',
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Expanded(
                                    child: TextField(
                                      controller:
                                          lines[i]['credit']
                                              as TextEditingController,
                                      decoration: const InputDecoration(
                                        labelText: 'Haber BOB',
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              DropdownButtonFormField<String>(
                                initialValue:
                                    lines[i]['cash_activity'] as String?,
                                decoration: const InputDecoration(
                                  labelText:
                                      'Actividad de efectivo (solo disponibilidades)',
                                ),
                                items: const [
                                  DropdownMenuItem<String>(
                                    value: null,
                                    child: Text('No corresponde'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'operation',
                                    child: Text('Operación'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'investment',
                                    child: Text('Inversión'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'financing',
                                    child: Text('Financiamiento'),
                                  ),
                                ],
                                onChanged: (v) =>
                                    update(() => lines[i]['cash_activity'] = v),
                              ),
                            ],
                          ),
                        ),
                      ),
                    OutlinedButton.icon(
                      onPressed: () => update(
                        () => lines.add({
                          'account_id': null,
                          'debit': TextEditingController(),
                          'credit': TextEditingController(),
                          'cash_activity': null,
                        }),
                      ),
                      icon: const Icon(Icons.add),
                      label: const Text('Añadir línea'),
                    ),
                  ],
                  if (issue != null)
                    Text(issue!, style: const TextStyle(color: Colors.red)),
                  if (saving) const LinearProgressIndicator(),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: saving ? null : () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: saving
                  ? null
                  : () async {
                      update(() {
                        saving = true;
                        issue = null;
                      });
                      try {
                        Json body;
                        if (type == 'account') {
                          body = {
                            'code': cs['code']!.text.trim(),
                            'name': cs['name']!.text.trim(),
                            'kind': kind,
                            'section': section,
                            'is_cash': cash,
                            'parent_id': parent,
                            'liquidity_order': int.parse(
                              cs['liquidity_order']!.text,
                            ),
                          };
                        } else if (type == 'disclosure') {
                          body = {
                            'year': int.parse(cs['year']!.text),
                            'kind': kind,
                            'title': cs['title']!.text.trim(),
                            'body': cs['body']!.text.trim(),
                            'risk': risk,
                            'account_id': noteAccount,
                          };
                        } else {
                          body = {
                            for (final k in cs.keys) k: cs[k]!.text.trim(),
                            'entry_type': entryType,
                            'equity_event': equityEvent,
                            'lines': [
                              for (final l in lines)
                                {
                                  'account_id': l['account_id'],
                                  'debit':
                                      (l['debit'] as TextEditingController).text
                                          .trim()
                                          .isEmpty
                                      ? '0.00'
                                      : (l['debit'] as TextEditingController)
                                            .text
                                            .trim(),
                                  'credit':
                                      (l['credit'] as TextEditingController)
                                          .text
                                          .trim()
                                          .isEmpty
                                      ? '0.00'
                                      : (l['credit'] as TextEditingController)
                                            .text
                                            .trim(),
                                  'cash_activity': l['cash_activity'],
                                },
                            ],
                          };
                        }
                        await api.post(
                          'accounting/${type == 'account'
                              ? 'accounts'
                              : type == 'disclosure'
                              ? 'disclosures'
                              : 'entries'}',
                          data: body,
                        );
                        if (context.mounted) Navigator.pop(context);
                      } catch (e) {
                        update(() {
                          issue = '$e';
                          saving = false;
                        });
                      }
                    },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );
    for (final c in cs.values) {
      c.dispose();
    }
    for (final l in lines) {
      (l['debit'] as TextEditingController).dispose();
      (l['credit'] as TextEditingController).dispose();
    }
    await load();
  }

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [
      const Text(
        'Libro contable separado del presupuesto. Los estados se calculan a fecha exacta con asientos de partida doble y conservan las cuentas contingentes y de orden por separado.',
      ),
      const SizedBox(height: 16),
      Wrap(
        spacing: 12,
        runSpacing: 12,
        crossAxisAlignment: WrapCrossAlignment.center,
        children: [
          SizedBox(
            width: 210,
            child: TextField(
              controller: cutoff,
              decoration: const InputDecoration(
                labelText: 'Fecha de corte AAAA-MM-DD',
              ),
            ),
          ),
          FilledButton(
            onPressed: busy ? null : load,
            child: const Text('Consultar estados'),
          ),
          if (ref.watch(authProvider).valueOrNull?.isAdmin ?? false) ...[
            OutlinedButton(
              onPressed: busy || error != null ? null : () => form('account'),
              child: const Text('Añadir cuenta'),
            ),
            OutlinedButton(
              onPressed: busy || accounts.isEmpty ? null : () => form('entry'),
              child: const Text('Registrar asiento'),
            ),
            OutlinedButton(
              onPressed: busy || error != null
                  ? null
                  : () => form('disclosure'),
              child: const Text('Dictamen o nota'),
            ),
          ],
        ],
      ),
      const SizedBox(height: 16),
      if (busy) const LinearProgressIndicator(),
      if (error != null)
        Text(error!, style: const TextStyle(color: Colors.red)),
      if (statements.isNotEmpty) ReportTree(statements),
    ],
  );
}
