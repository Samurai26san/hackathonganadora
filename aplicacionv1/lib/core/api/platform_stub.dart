import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'dart:io';
import 'package:dio/dio.dart';

void configureBrowser(Dio dio) {
  final cookies = <String, String>{};
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (request, handler) {
        if (cookies.isNotEmpty) {
          request.headers['Cookie'] = cookies.entries
              .map((e) => '${e.key}=${e.value}')
              .join('; ');
        }
        handler.next(request);
      },
      onResponse: (response, handler) {
        for (final header in response.headers['set-cookie'] ?? <String>[]) {
          final cookie = Cookie.fromSetCookieValue(header);
          if (cookie.name != 'exb_session' && cookie.name != 'exb_oidc_state')
            continue;
          if (cookie.maxAge == 0 || cookie.value.isEmpty) {
            cookies.remove(cookie.name);
          } else {
            cookies[cookie.name] = cookie.value;
          }
        }
        handler.next(response);
      },
    ),
  );
}

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

const _files = MethodChannel('exb/files');
Future<void> downloadBytes(
  Uint8List bytes,
  String filename,
  String mime,
) async {
  await _files.invokeMethod<bool>('save', {
    'bytes': bytes,
    'filename': filename,
    'mime': mime,
  });
}

Future<Uint8List?> pickWorkbook() =>
    _files.invokeMethod<Uint8List>('pickWorkbook');
