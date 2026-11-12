import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'models.dart';
import 'platform_stub.dart'
    if (dart.library.js_interop) 'platform_web.dart'
    as platform;

final apiProvider = Provider<ApiClient>((ref) => ApiClient());

class ApiError implements Exception {
  const ApiError(this.message, {this.status});
  final String message;
  final int? status;
  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({Dio? client})
    : dio =
          client ??
          Dio(
            BaseOptions(
              baseUrl: Uri.base
                  .resolve(
                    const String.fromEnvironment(
                      'API_BASE_URL',
                      defaultValue: '/api/v1/',
                    ),
                  )
                  .toString(),
              connectTimeout: const Duration(seconds: 8),
              receiveTimeout: const Duration(seconds: 100),
            ),
          ) {
    if (client == null) platform.configureBrowser(dio);
  }
  final Dio dio;

  Future<dynamic> get(String path, {Json? query}) async {
    try {
      final target = path.startsWith('/')
          ? Uri.parse(dio.options.baseUrl).resolve(path).toString()
          : path;
      return (await dio.get<dynamic>(target, queryParameters: query)).data;
    } on DioException catch (error) {
      throw mapError(error);
    }
  }

  Future<dynamic> post(String path, {Object? data}) async {
    try {
      return (await dio.post<dynamic>(path, data: data)).data;
    } on DioException catch (error) {
      throw mapError(error);
    }
  }

  ApiError mapError(DioException error) {
    final data = error.response?.data;
    return ApiError(
      data is Map && data['detail'] is String
          ? data['detail'] as String
          : error.response?.statusCode == 422
          ? 'Revisa los campos del formulario: categorías, importe, fecha y motivo.'
          : 'No se pudo conectar con el servidor. Revisa la conexión e inténtalo nuevamente.',
      status: error.response?.statusCode,
    );
  }

  Future<AppUser> me() async => AppUser.fromJson(await get('auth/me') as Json);

  Future<dynamic> put(String path, {Object? data}) async {
    try {
      return (await dio.put<dynamic>(path, data: data)).data;
    } on DioException catch (error) {
      throw mapError(error);
    }
  }

  Future<void> downloadJson(String path, String filename) async {
    final data = await get(path);
    platform.downloadBytes(
      Uint8List.fromList(
        utf8.encode(const JsonEncoder.withIndent('  ').convert(data)),
      ),
      filename,
      'application/json',
    );
  }

  Future<Catalogs> catalogs() async => Catalogs(await get('catalogs') as Json);
  Future<FinancialReport> report(
    String type,
    BudgetFilters filters, {
    int? compareYear,
  }) async => FinancialReport.fromJson(
    await get(
          type == 'compare' ? 'budget/compare' : 'budget/execution/$type',
          query: {
            ...filters.toQuery(),
            if (compareYear != null) 'years': '${filters.year},$compareYear',
          },
        )
        as Json,
  );

  Future<void> export(
    String report,
    String format,
    BudgetFilters filters, {
    int? compareYear,
  }) async {
    try {
      final response = await dio.post<List<int>>(
        'reports/export',
        data: {
          'report': report,
          'format': format,
          'filters': {
            ...filters.toJson(),
            if (compareYear != null) 'years': [filters.year, compareYear],
          },
        },
        options: Options(responseType: ResponseType.bytes),
      );
      final extension = format == 'excel' ? 'xlsx' : format;
      platform.downloadBytes(
        Uint8List.fromList(response.data!),
        'exb-$report.$extension',
        response.headers.value('content-type') ?? 'application/octet-stream',
      );
    } on DioException catch (error) {
      throw mapError(error);
    }
  }

  Stream<Json> chat(Json body, CancelToken cancelToken) async* {
    try {
      yield* parseSse(platform.chatBytes(dio, body, cancelToken));
    } on DioException catch (error) {
      throw mapError(error);
    }
  }

  Future<Json?> previewWorkbook() async {
    final bytes = await platform.pickWorkbook();
    if (bytes == null) return null;
    return await post(
          'imports/preview',
          data: FormData.fromMap({
            'file': MultipartFile.fromBytes(
              bytes,
              filename: 'base-contable.xlsx',
            ),
          }),
        )
        as Json;
  }
}

Stream<Json> parseSse(Stream<List<int>> bytes) async* {
  var type = 'message';
  final data = <String>[];
  await for (final line
      in bytes.transform(utf8.decoder).transform(const LineSplitter())) {
    if (line.startsWith(':')) continue;
    if (line.startsWith('event:')) type = line.substring(6).trim();
    if (line.startsWith('data:')) data.add(line.substring(5).trimLeft());
    if (line.isEmpty && data.isNotEmpty) {
      final json = jsonDecode(data.join('\n')) as Json;
      yield {'event': type, ...json};
      data.clear();
      type = 'message';
    }
  }
  if (data.isNotEmpty) {
    yield {'event': type, ...jsonDecode(data.join('\n')) as Json};
  }
}
