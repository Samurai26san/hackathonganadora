import 'dart:typed_data';
import 'package:dio/dio.dart';

void configureBrowser(Dio dio) {}
Stream<List<int>> chatBytes(
  Dio dio,
  Map<String, dynamic> body,
  CancelToken cancelToken,
) async* {
  final response = await dio.post<ResponseBody>(
    'chat/stream',
    data: body,
    cancelToken: cancelToken,
    options: Options(responseType: ResponseType.stream),
  );
  yield* response.data!.stream;
}

void downloadBytes(Uint8List bytes, String filename, String mime) {}
Future<Uint8List?> pickWorkbook() async => null;
String? readSetting(String key) => null;
void writeSetting(String key, String value) {}
Future<bool> shareBytes(
  Uint8List bytes,
  String filename,
  String mime,
  String title,
) async => false;
