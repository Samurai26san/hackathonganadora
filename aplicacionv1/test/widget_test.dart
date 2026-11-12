import 'dart:convert';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:aplicacionv1/core/api/api_client.dart';
import 'package:aplicacionv1/core/api/models.dart';
import 'package:aplicacionv1/core/utils/money.dart';
import 'package:aplicacionv1/main.dart';

class TestApi extends ApiClient {
  TestApi()
    : super(client: Dio(BaseOptions(baseUrl: 'http://localhost/api/v1/')));
  bool authenticated = false;
  final user = const AppUser(
    name: 'Técnico de prueba',
    email: 'tecnico@exb.demo',
    role: 'analyst',
  );
  @override
  Future<AppUser> me() async {
    if (!authenticated) throw const ApiError('Inicia sesión', status: 401);
    return user;
  }

  @override
  Future<dynamic> get(String path, {Json? query}) async {
    if (path == '/health') return <String, dynamic>{'auth_mode': 'demo'};
    if (path == 'sessions') return <dynamic>[];
    throw const ApiError('Ruta de prueba no definida');
  }

  @override
  Future<dynamic> post(String path, {Object? data}) async {
    if (path == 'auth/logout') {
      authenticated = false;
      return {'ok': true};
    }
    authenticated = true;
    return <String, dynamic>{
      'full_name': user.name,
      'email': user.email,
      'role': user.role,
    };
  }

  @override
  Future<Catalogs> catalogs() async => Catalogs({
    'years': [2026],
    'reports': [
      for (final pair in [
        ('account', 'Ejecución por rubro y cuenta'),
        ('financier', 'Ejecución por financiador'),
        ('area', 'Ejecución por área y financiador'),
        ('region', 'Ejecución por región'),
        ('monthly', 'Ejecución por mes'),
        ('movements', 'Detalle de movimientos'),
        ('summary', 'Resumen general consolidado'),
      ])
        {'id': pair.$1, 'title': pair.$2},
    ],
    'region': [
      {'id': 1, 'name': 'LP'},
    ],
    'area': [
      {'id': 1, 'name': 'Educación'},
    ],
    'rubro': [
      {'id': 1, 'name': '1. Viajes'},
    ],
    'cuenta': [
      {'id': 1, 'name': 'Pasajes', 'rubro_id': 1},
    ],
    'financier': [
      {'id': 1, 'name': 'Catalyst'},
    ],
    'months': [
      {'id': 3, 'name': 'Marzo'},
    ],
  });
  @override
  Future<FinancialReport> report(
    String type,
    BudgetFilters filters, {
    int? compareYear,
  }) async => FinancialReport.fromJson({
    'report_type': type,
    'title': 'Informe de prueba',
    'metadata': {'total_count': 1, 'filters': filters.toJson()},
    'summary': {
      'initial_budget': '100.10',
      'modifications': '0.00',
      'current_budget': '100.10',
      'executed': '0.30',
      'balance': '99.80',
      'execution_percentage': '0.30',
    },
    'rows': [
      {
        'labels': {
          type == 'monthly' ? 'month' : 'rubro': type == 'monthly'
              ? 'Marzo'
              : '1. Viajes',
        },
        'values': {
          'current_budget': '100.10',
          'executed': '0.30',
          'balance': '99.80',
          'execution_percentage': '0.30',
        },
        'dimensions': {'rubro': 1, 'cuenta': 1},
      },
    ],
  });
}

void main() {
  test('salud usa la raíz y los informes conservan el prefijo API', () async {
    final requests = <Uri>[];
    final dio = Dio(BaseOptions(baseUrl: 'http://localhost:8080/api/v1/'));
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          requests.add(options.uri);
          handler.resolve(
            Response<dynamic>(
              requestOptions: options,
              data: <String, dynamic>{},
            ),
          );
        },
      ),
    );
    final api = ApiClient(client: dio);
    await api.get('/health');
    await api.get('catalogs');
    expect(requests.map((uri) => uri.path).toList(), [
      '/health',
      '/api/v1/catalogs',
    ]);
  });
  test('moneda exacta, redondeo y rechazo de doubles monetarios', () {
    expect((Money.parse('0.10') + Money.parse('0.20')).decimal, '0.30');
    expect(Money.parse('3163379.01').currency, 'Bs 3.163.379,01');
    expect(Money.parse('-10.105').decimal, '-10.11');
    expect(() => Money.parse(0.10), throwsFormatException);
  });
  test('SSE conserva UTF-8 y eventos partidos entre chunks', () async {
    final bytes = utf8.encode(
      'event: delta\r\ndata: {"event":"delta","data":"Ejecución","session_id":"s1"}\r\n\r\nevent: done\ndata: {"data":{},"session_id":"s1"}\n\n',
    );
    final chunks = <List<int>>[
      for (var index = 0; index < bytes.length; index += 3)
        bytes.sublist(index, (index + 3).clamp(0, bytes.length)),
    ];
    final events = await parseSse(Stream.fromIterable(chunks)).toList();
    expect(events.first['data'], 'Ejecución');
    expect(events.last['event'], 'done');
    expect(events.last['session_id'], 's1');
  });
  test('los filtros conservan gestión y eliminan cuenta al cambiar rubro', () {
    final filter = const BudgetFilters(
      year: 2026,
      account: 3,
    ).change('rubro', 2);
    expect(filter.year, 2026);
    expect(filter.account, isNull);
    expect(filter.toJson()['rubro_ids'], [2]);
  });

  testWidgets(
    'login, navegación, importes y gestión única sin comparación inventada',
    (tester) async {
      tester.view.physicalSize = const Size(1440, 1050);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final api = TestApi();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [apiProvider.overrideWithValue(api)],
          child: const ExbApp(),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Correo electrónico'), findsOneWidget);
      await tester.ensureVisible(find.text('Técnico'));
      await tester.tap(find.text('Técnico'));
      await tester.pump();
      await tester.ensureVisible(find.text('Ingresar al sistema'));
      await tester.tap(find.text('Ingresar al sistema'));
      await tester.pumpAndSettle();
      expect(find.text('Bs 100,10'), findsWidgets);
      expect(find.text('Panel financiero'), findsWidgets);
      await tester.tap(find.text('Gestiones').first);
      await tester.pumpAndSettle();
      expect(
        find.text('Por ahora, una gestión. Sin comparaciones inventadas.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );

  testWidgets('login y panel responden a 375 px sin desbordar', (tester) async {
    tester.view.physicalSize = const Size(375, 900);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final api = TestApi()..authenticated = true;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [apiProvider.overrideWithValue(api)],
        child: const ExbApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byTooltip('Abrir o cerrar menú'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.byTooltip('Abrir o cerrar menú'));
    await tester.pumpAndSettle();
    expect(find.text('Presupuesto'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
