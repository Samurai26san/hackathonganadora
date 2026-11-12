import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/models.dart';
import '../../core/theme/app_theme.dart';
import '../../features/dashboard/providers.dart';

class FilterBar extends ConsumerStatefulWidget {
  const FilterBar({super.key, required this.mode});
  final String mode;
  @override
  ConsumerState<FilterBar> createState() => _FilterBarState();
}

class _FilterBarState extends ConsumerState<FilterBar> {
  bool advanced = false;
  @override
  Widget build(BuildContext context) {
    final filters = ref.watch(filtersProvider);
    final catalogs = ref.watch(catalogsProvider).valueOrNull;
    if (catalogs == null) return const SizedBox.shrink();
    void change(String key, Object? value) =>
        ref.read(filtersProvider.notifier).state = filters.change(key, value);
    Widget select(String label, String key, String catalog, int? value) {
      var items = catalogs.items(catalog);
      if (key == 'account' && filters.rubro != null) {
        items = items.where((item) => item.parent == filters.rubro).toList();
      }
      return FilterSelect(
        label: label,
        value: value,
        items: items,
        onChanged: (id) => change(key, id),
      );
    }

    final controls = <Widget>[
      if (widget.mode == 'dashboard')
        FilterSelect(
          label: 'Gestión',
          value: filters.year,
          allowAll: false,
          items: catalogs.years
              .map((year) => CatalogItem(year, '$year'))
              .toList(),
          onChanged: (year) {
            if (year != null) change('year', year);
          },
        ),
      if (widget.mode == 'movements')
        SizedBox(
          width: 260,
          child: TextFormField(
            key: ValueKey('search:${filters.search}'),
            initialValue: filters.search,
            decoration: const InputDecoration(
              labelText: 'Buscar movimiento',
              hintText: 'Concepto o comprobante',
              prefixIcon: Icon(Icons.search, size: 20),
            ),
            onFieldSubmitted: (value) => change('search', value.trim()),
          ),
        ),
      select('Financiador', 'financier', 'financier', filters.financier),
      if (widget.mode == 'budget') ...[
        select('Rubro', 'rubro', 'rubro', filters.rubro),
        select('Área', 'area', 'area', filters.area),
      ],
      if (widget.mode == 'reports')
        select('Período', 'month', 'months', filters.month),
      if (widget.mode == 'movements')
        OutlinedButton.icon(
          onPressed: () async {
            final range = await showDateRangePicker(
              context: context,
              firstDate: DateTime(filters.year),
              lastDate: DateTime(filters.year, 12, 31),
              helpText: 'Período de movimientos',
            );
            if (range != null) {
              ref.read(filtersProvider.notifier).state = filters
                  .change(
                    'dateFrom',
                    range.start.toIso8601String().substring(0, 10),
                  )
                  .change(
                    'dateTo',
                    range.end.toIso8601String().substring(0, 10),
                  );
            }
          },
          icon: const Icon(Icons.date_range_outlined, size: 18),
          label: Text(
            filters.dateFrom == null
                ? 'Rango de fechas'
                : '${filters.dateFrom} / ${filters.dateTo}',
          ),
        ),
      if (widget.mode != 'dashboard')
        OutlinedButton.icon(
          onPressed: () => setState(() => advanced = !advanced),
          icon: Icon(advanced ? Icons.tune : Icons.tune_outlined, size: 18),
          label: const Text('Filtros avanzados'),
        ),
      TextButton.icon(
        onPressed: () => ref.read(filtersProvider.notifier).state =
            BudgetFilters(year: filters.year),
        icon: const Icon(Icons.restart_alt, size: 17),
        label: const Text('Limpiar'),
      ),
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Wrap(
          spacing: 12,
          runSpacing: 16,
          crossAxisAlignment: WrapCrossAlignment.end,
          children: controls,
        ),
        if (advanced && widget.mode != 'dashboard')
          Padding(
            padding: const EdgeInsets.only(top: 18),
            child: Wrap(
              spacing: 12,
              runSpacing: 16,
              children: [
                select('Región', 'region', 'region', filters.region),
                if (widget.mode != 'budget')
                  select('Área', 'area', 'area', filters.area),
                if (widget.mode != 'budget')
                  select('Rubro', 'rubro', 'rubro', filters.rubro),
                select('Cuenta', 'account', 'cuenta', filters.account),
                if (widget.mode != 'reports')
                  select('Mes', 'month', 'months', filters.month),
              ],
            ),
          ),
        if ([
              filters.financier,
              filters.region,
              filters.area,
              filters.rubro,
              filters.account,
              filters.month,
              filters.dateFrom,
            ].any((value) => value != null) ||
            filters.search.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 14),
            child: Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final entry in <String, (String, String, int?)>{
                  'financier': ('Financiador', 'financier', filters.financier),
                  'region': ('Región', 'region', filters.region),
                  'area': ('Área', 'area', filters.area),
                  'rubro': ('Rubro', 'rubro', filters.rubro),
                  'account': ('Cuenta', 'cuenta', filters.account),
                  'month': ('Mes', 'months', filters.month),
                }.entries)
                  if (entry.value.$3 != null)
                    InputChip(
                      label: Text(
                        '${entry.value.$1}: ${catalogs.items(entry.value.$2).where((item) => item.id == entry.value.$3).firstOrNull?.name ?? entry.value.$3}',
                      ),
                      onDeleted: () => change(entry.key, null),
                    ),
                if (filters.search.isNotEmpty)
                  InputChip(
                    label: Text('Búsqueda: ${filters.search}'),
                    onDeleted: () => change('search', ''),
                  ),
                if (filters.dateFrom != null)
                  InputChip(
                    label: Text('Desde ${filters.dateFrom}'),
                    onDeleted: () => ref.read(filtersProvider.notifier).state =
                        filters.change('dateFrom', null).change('dateTo', null),
                  ),
              ],
            ),
          ),
      ],
    );
  }
}

class FilterSelect extends StatelessWidget {
  const FilterSelect({
    super.key,
    required this.label,
    required this.value,
    required this.items,
    required this.onChanged,
    this.allowAll = true,
    this.width = 210,
  });
  final String label;
  final int? value;
  final List<CatalogItem> items;
  final ValueChanged<int?> onChanged;
  final bool allowAll;
  final double width;
  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    child: DropdownButtonFormField<int>(
      key: ValueKey('$label:$value:${items.length}'),
      initialValue: items.any((item) => item.id == value) ? value : null,
      isExpanded: true,
      menuMaxHeight: 360,
      decoration: InputDecoration(labelText: label),
      icon: const Icon(
        Icons.keyboard_arrow_down,
        color: ExbColors.green,
        size: 20,
      ),
      items: [
        if (allowAll)
          const DropdownMenuItem<int>(
            value: null,
            child: Text('Todos', overflow: TextOverflow.ellipsis),
          ),
        for (final item in items)
          DropdownMenuItem<int>(
            value: item.id,
            child: Text(
              item.name,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12),
            ),
          ),
      ],
      onChanged: onChanged,
    ),
  );
}
