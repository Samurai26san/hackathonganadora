import '../utils/money.dart';

typedef Json = Map<String, dynamic>;

class AppUser {
  const AppUser({required this.name, required this.email, required this.role});
  final String name, email, role;
  bool get isAdmin => role == 'admin';
  String get roleLabel => isAdmin ? 'Administrador' : 'Técnico';
  factory AppUser.fromJson(Json json) => AppUser(
    name: json['full_name'] as String,
    email: json['email'] as String,
    role: json['role'] as String,
  );
}

class CatalogItem {
  const CatalogItem(this.id, this.name, {this.parent});
  final int id;
  final String name;
  final int? parent;
}

class Catalogs {
  Catalogs(this.json);
  final Json json;
  List<int> get years => (json['years'] as List<dynamic>).cast<int>();
  List<CatalogItem> items(String key) => (json[key] as List<dynamic>? ?? [])
      .map(
        (dynamic row) => CatalogItem(
          row['id'] as int,
          row['name'] as String,
          parent: row['rubro_id'] as int?,
        ),
      )
      .toList();
  List<Json> get reports => (json['reports'] as List<dynamic>).cast<Json>();
}

class BudgetFilters {
  const BudgetFilters({
    this.year = 2026,
    this.financier,
    this.region,
    this.area,
    this.rubro,
    this.account,
    this.month,
    this.search = '',
    this.validationStatus,
    this.dateFrom,
    this.dateTo,
    this.page = 1,
    this.metric = 'executed',
  });
  final int year;
  final int? financier, region, area, rubro, account, month;
  final String search;
  final String? dateFrom, dateTo, validationStatus;
  final int page;
  final String metric;

  Json toJson() => {
    'years': [year],
    if (financier != null) 'financier_ids': [financier],
    if (region != null) 'region_ids': [region],
    if (area != null) 'area_ids': [area],
    if (rubro != null) 'rubro_ids': [rubro],
    if (account != null) 'cuenta_ids': [account],
    if (month != null) 'months': [month],
    'search': search,
    if (validationStatus != null) 'validation_status': validationStatus,
    'page': page,
    'metric': metric,
    if (dateFrom != null) 'date_from': dateFrom,
    if (dateTo != null) 'date_to': dateTo,
  };

  Json toQuery() => toJson().map(
    (key, dynamic value) =>
        MapEntry(key, value is List ? value.join(',') : value),
  );

  BudgetFilters change(String key, Object? value) {
    final next = <String, Object?>{
      'year': year,
      'financier': financier,
      'region': region,
      'area': area,
      'rubro': rubro,
      'account': account,
      'month': month,
      'search': search,
      'validationStatus': validationStatus,
      'dateFrom': dateFrom,
      'dateTo': dateTo,
      'page': 1,
      'metric': metric,
      key: value,
    };
    if (key == 'rubro') next['account'] = null;
    return BudgetFilters(
      year: next['year'] as int,
      financier: next['financier'] as int?,
      region: next['region'] as int?,
      area: next['area'] as int?,
      rubro: next['rubro'] as int?,
      account: next['account'] as int?,
      month: next['month'] as int?,
      search: next['search'] as String,
      validationStatus: next['validationStatus'] as String?,
      dateFrom: next['dateFrom'] as String?,
      dateTo: next['dateTo'] as String?,
      page: next['page'] as int,
      metric: next['metric'] as String,
    );
  }

  factory BudgetFilters.fromContext(Json json) => BudgetFilters(
    year: (json['years'] as List<dynamic>).first as int,
    financier: (json['financier_ids'] as List<dynamic>?)?.firstOrNull as int?,
    region: (json['region_ids'] as List<dynamic>?)?.firstOrNull as int?,
    area: (json['area_ids'] as List<dynamic>?)?.firstOrNull as int?,
    rubro: (json['rubro_ids'] as List<dynamic>?)?.firstOrNull as int?,
    account: (json['cuenta_ids'] as List<dynamic>?)?.firstOrNull as int?,
    month: (json['months'] as List<dynamic>?)?.firstOrNull as int?,
    search: json['search'] as String? ?? '',
    validationStatus: json['validation_status'] as String?,
    metric: json['metric'] as String? ?? 'executed',
    dateFrom: json['date_from'] as String?,
    dateTo: json['date_to'] as String?,
  );
}

class FinancialRow {
  FinancialRow({
    required this.labels,
    required this.values,
    this.dimensions = const {},
    this.details = const {},
  });
  final Map<String, String> labels;
  final Map<String, Money> values;
  final Map<String, int> dimensions;
  final Json details;
  factory FinancialRow.fromJson(Json json) => FinancialRow(
    labels: (json['labels'] as Json).map(
      (key, dynamic value) => MapEntry(key, '$value'),
    ),
    values: (json['values'] as Json).map(
      (key, dynamic value) => MapEntry(key, Money.parse(value)),
    ),
    dimensions: (json['dimensions'] as Json? ?? {}).map(
      (key, dynamic value) => MapEntry(key, value as int),
    ),
    details: json['details'] as Json? ?? {},
  );
}

class FinancialReport {
  FinancialReport({
    required this.type,
    required this.title,
    required this.summary,
    required this.rows,
    required this.metadata,
  });
  final String type, title;
  final Map<String, Money> summary;
  final List<FinancialRow> rows;
  final Json metadata;
  int get count => metadata['total_count'] as int? ?? rows.length;
  factory FinancialReport.fromJson(Json json) => FinancialReport(
    type: json['report_type'] as String,
    title: json['title'] as String,
    summary: (json['summary'] as Json).map(
      (key, dynamic value) => MapEntry(key, Money.parse(value)),
    ),
    rows: (json['rows'] as List<dynamic>)
        .map((dynamic row) => FinancialRow.fromJson(row as Json))
        .toList(),
    metadata: json['metadata'] as Json,
  );
}
