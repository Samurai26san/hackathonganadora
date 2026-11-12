import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/theme/app_theme.dart';
import '../../shared/widgets/financial_widgets.dart';
import '../dashboard/providers.dart';

final adminDataProvider = FutureProvider.autoDispose
    .family<List<dynamic>, String>(
      (ref, path) async =>
          await ref.read(apiProvider).get(path) as List<dynamic>,
    );

class AdminScreen extends ConsumerStatefulWidget {
  const AdminScreen({super.key});
  @override
  ConsumerState<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends ConsumerState<AdminScreen> {
  bool busy = false;
  Json? preview;
  String? error;
  int selected = 0;
  @override
  Widget build(BuildContext context) {
    final paths = ['', 'users', 'dictionary', '', 'audit/logs'];
    final data = paths[selected].isEmpty
        ? null
        : ref.watch(adminDataProvider(paths[selected]));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final tab in [
              'Fuente de datos',
              'Usuarios',
              'Diccionario',
              'Conocimiento',
              'Auditoría',
            ].indexed)
              ChoiceChip(
                label: Text(tab.$2),
                selected: selected == tab.$1,
                onSelected: (_) => setState(() => selected = tab.$1),
              ),
          ],
        ),
        const SizedBox(height: 24),
        if (selected == 0)
          Panel(
            title: 'Revisión de la base contable',
            subtitle:
                'Valida un archivo Excel sin modificar los datos de la institución.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'En esta fase, las cargas financieras se realizan por el comando de ingesta del servidor. La vista previa comprueba encabezados, etiquetas, meses, fechas e importes; no reemplaza ninguna gestión.',
                  style: TextStyle(height: 1.8, color: ExbColors.secondaryText),
                ),
                const SizedBox(height: 20),
                FilledButton.icon(
                  onPressed: busy
                      ? null
                      : () async {
                          setState(() {
                            busy = true;
                            error = null;
                          });
                          try {
                            final value = await ref
                                .read(apiProvider)
                                .previewWorkbook();
                            if (mounted) setState(() => preview = value);
                          } catch (value) {
                            if (mounted) setState(() => error = '$value');
                          } finally {
                            if (mounted) setState(() => busy = false);
                          }
                        },
                  icon: const Icon(Icons.upload_file_outlined),
                  label: Text(
                    busy ? 'Validando archivo…' : 'Seleccionar Excel (.xlsx)',
                  ),
                ),
                if (error != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 18),
                    child: Text(
                      error!,
                      style: const TextStyle(color: ExbColors.amber),
                    ),
                  ),
                if (preview != null) ...[
                  const SizedBox(height: 24),
                  for (final entry in preview!.entries)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: SelectableText('${entry.key}: ${entry.value}'),
                    ),
                ],
              ],
            ),
          ),
        if (selected == 3)
          Panel(
            title: 'Biblioteca institucional de Juku',
            subtitle:
                'Solo documentos autorizados. Las fuentes se citan al consultar.',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'El servidor puede ingerir PDF, DOCX, TXT y Markdown desde data_docs. También puedes incorporar un fragmento institucional identificado. TEI debe estar disponible para generar embeddings reales.',
                  style: TextStyle(color: ExbColors.secondaryText, height: 1.7),
                ),
                const SizedBox(height: 20),
                FilledButton.icon(
                  onPressed: () => _knowledgeDialog(),
                  icon: const Icon(Icons.menu_book_outlined),
                  label: const Text('Agregar texto institucional'),
                ),
              ],
            ),
          ),
        if (data != null)
          data.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (value, _) => MessageState(
              title: 'No pudimos cargar la información.',
              detail: '$value',
              onRetry: () => ref.invalidate(adminDataProvider(paths[selected])),
            ),
            data: (rows) => Panel(
              title: [
                '',
                'Usuarios y alcances',
                'Diccionario institucional',
                '',
                'Registro de auditoría',
              ][selected],
              action: selected == 1 || selected == 2
                  ? IconButton(
                      tooltip: 'Agregar registro',
                      onPressed: () =>
                          selected == 1 ? _userDialog() : _dictionaryDialog(),
                      icon: const Icon(Icons.add_circle_outline),
                    )
                  : IconButton(
                      tooltip: 'Actualizar auditoría',
                      onPressed: () =>
                          ref.invalidate(adminDataProvider('audit/logs')),
                      icon: const Icon(Icons.refresh),
                    ),
              child: rows.isEmpty
                  ? const Text('No hay registros.')
                  : Column(
                      children: [
                        for (final dynamic row in rows)
                          ListTile(
                            contentPadding: EdgeInsets.zero,
                            leading: Icon(
                              selected == 1
                                  ? Icons.person_outline
                                  : selected == 2
                                  ? Icons.book_outlined
                                  : Icons.history,
                              color: ExbColors.green,
                            ),
                            title: Text(
                              '${row[selected == 1
                                  ? 'full_name'
                                  : selected == 2
                                  ? 'termino_usuario'
                                  : 'action']}',
                              style: const TextStyle(fontSize: 14),
                            ),
                            subtitle: Text(
                              selected == 1
                                  ? '${row['email']} · ${row['role']} · ${row['is_active'] == true ? 'Activo' : 'Inactivo'}\nAlcance: ${row['scopes']}'
                                  : selected == 2
                                  ? '${row['descripcion']} · v${row['version']}'
                                  : '${row['timestamp']} · ${row['status']} · ${row['resource']}',
                              style: const TextStyle(fontSize: 11),
                            ),
                            trailing: selected == 1 || selected == 2
                                ? IconButton(
                                    tooltip: 'Editar registro',
                                    onPressed: () => selected == 1
                                        ? _userDialog(row as Json)
                                        : _dictionaryDialog(row as Json),
                                    icon: const Icon(
                                      Icons.edit_outlined,
                                      size: 19,
                                    ),
                                  )
                                : null,
                          ),
                      ],
                    ),
            ),
          ),
      ],
    );
  }

  Future<void> _userDialog([Json? current]) async {
    final email = TextEditingController(
      text: current?['email'] as String? ?? '',
    );
    final name = TextEditingController(
      text: current?['full_name'] as String? ?? '',
    );
    var role = current?['role'] as String? ?? 'viewer';
    var active = current?['is_active'] as bool? ?? true;
    final Json scopes = current?['scopes'] as Json? ?? {'region_ids': <int>[]};
    var allRegions = scopes['region_ids'] == null;
    final selectedRegions = <int>{
      ...(scopes['region_ids'] as List<dynamic>? ?? []).cast<int>(),
    };
    final regions =
        ref.read(catalogsProvider).valueOrNull?.items('region') ?? [];
    final body = await showDialog<Json>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialog) => AlertDialog(
          title: Text(current == null ? 'Habilitar cuenta' : 'Editar cuenta'),
          content: SizedBox(
            width: 460,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: email,
                    decoration: const InputDecoration(
                      labelText: 'Correo institucional',
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: name,
                    decoration: const InputDecoration(
                      labelText: 'Nombre completo',
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    initialValue: role,
                    decoration: const InputDecoration(labelText: 'Rol'),
                    items: const [
                      DropdownMenuItem(
                        value: 'viewer',
                        child: Text('Consulta'),
                      ),
                      DropdownMenuItem(
                        value: 'analyst',
                        child: Text('Técnico'),
                      ),
                      DropdownMenuItem(
                        value: 'admin',
                        child: Text('Administrador'),
                      ),
                    ],
                    onChanged: (value) => setDialog(() => role = value!),
                  ),
                  SwitchListTile(
                    title: const Text('Cuenta activa'),
                    value: active,
                    onChanged: (value) => setDialog(() => active = value),
                  ),
                  CheckboxListTile(
                    title: const Text('Todas las regiones'),
                    value: allRegions,
                    onChanged: (value) => setDialog(() => allRegions = value!),
                  ),
                  if (!allRegions) ...[
                    const Text(
                      'Sin regiones seleccionadas: no se permite consultar datos.',
                      style: TextStyle(fontSize: 11, color: ExbColors.amber),
                    ),
                    for (final region in regions)
                      CheckboxListTile(
                        title: Text(region.name),
                        value: selectedRegions.contains(region.id),
                        onChanged: (value) => setDialog(() {
                          value!
                              ? selectedRegions.add(region.id)
                              : selectedRegions.remove(region.id);
                        }),
                      ),
                  ],
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
            FilledButton(
              onPressed: () {
                if (!email.text.contains('@') || name.text.trim().isEmpty) {
                  return;
                }
                Navigator.pop(context, {
                  'email': email.text.trim(),
                  'full_name': name.text.trim(),
                  'role': role,
                  'is_active': active,
                  'region_ids': allRegions ? null : selectedRegions.toList(),
                  'area_ids': scopes['area_ids'],
                  'financier_ids': scopes['financier_ids'],
                });
              },
              child: const Text('Guardar'),
            ),
          ],
        ),
      ),
    );
    email.dispose();
    name.dispose();
    if (body != null) {
      await _save(
        current == null ? 'users' : 'users/${current['id']}',
        body,
        'users',
        update: current != null,
      );
    }
  }

  Future<void> _dictionaryDialog([Json? current]) async {
    final fields = {
      'termino_usuario': 'Término del usuario',
      'columna_canonica': 'Columna canónica',
      'tabla_origen': 'Tabla de origen',
      'descripcion': 'Descripción institucional',
    };
    final controls = fields.map(
      (key, _) => MapEntry(
        key,
        TextEditingController(text: current?[key] as String? ?? ''),
      ),
    );
    final body = await showDialog<Json>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Definición institucional'),
        content: SizedBox(
          width: 480,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final field in fields.entries)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: TextField(
                      controller: controls[field.key],
                      decoration: InputDecoration(labelText: field.value),
                      maxLines: field.key == 'descripcion' ? 3 : 1,
                    ),
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () {
              if (controls.values.any((value) => value.text.trim().isEmpty)) {
                return;
              }
              Navigator.pop(context, {
                for (final entry in controls.entries)
                  entry.key: entry.value.text.trim(),
                'sinonimos_json': current?['sinonimos_json'] ?? <String>[],
                'activo': true,
              });
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
    for (final control in controls.values) {
      control.dispose();
    }
    if (body != null) {
      await _save(
        current == null ? 'dictionary' : 'dictionary/${current['id']}',
        body,
        'dictionary',
        update: current != null,
      );
    }
  }

  Future<void> _knowledgeDialog() async {
    final title = TextEditingController(), content = TextEditingController();
    final body = await showDialog<Json>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Agregar fuente institucional'),
        content: SizedBox(
          width: 540,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: title,
                decoration: const InputDecoration(
                  labelText: 'Título de la fuente',
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: content,
                maxLines: 8,
                decoration: const InputDecoration(
                  labelText: 'Texto institucional autorizado',
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () {
              if (title.text.trim().isEmpty ||
                  content.text.trim().length < 10) {
                return;
              }
              Navigator.pop(context, {
                'source_id': title.text.trim().toLowerCase().replaceAll(
                  RegExp(r'\s+'),
                  '-',
                ),
                'source_title': title.text.trim(),
                'source_type': 'manual',
                'content': content.text.trim(),
              });
            },
            child: const Text('Ingerir documento'),
          ),
        ],
      ),
    );
    title.dispose();
    content.dispose();
    if (body != null) await _save('knowledge/ingest', body, '');
  }

  Future<void> _save(
    String path,
    Json body,
    String refresh, {
    bool update = false,
  }) async {
    try {
      final api = ref.read(apiProvider);
      if (update) {
        await api.dio.put<dynamic>(path, data: body);
      } else {
        await api.post(path, data: body);
      }
      if (refresh.isNotEmpty) ref.invalidate(adminDataProvider(refresh));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Operación completada y registrada en auditoría.'),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$error')));
      }
    }
  }
}
