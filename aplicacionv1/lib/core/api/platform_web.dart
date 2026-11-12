import 'dart:async';
import 'dart:convert';
import 'dart:js_interop';
import 'dart:typed_data';
import 'package:dio/browser.dart';
import 'package:dio/dio.dart';
import 'package:web/web.dart' as web;
import 'package:http/browser_client.dart';
import 'package:http/http.dart' as http;

void configureBrowser(Dio dio) {
  dio.httpClientAdapter = BrowserHttpClientAdapter(withCredentials: true);
}

Stream<List<int>> chatBytes(
  Dio dio,
  Map<String, dynamic> body,
  CancelToken cancelToken,
) async* {
  final client = BrowserClient()..withCredentials = true;
  unawaited(cancelToken.whenCancel.then((_) => client.close()));
  try {
    final request =
        http.Request('POST', Uri.parse('${dio.options.baseUrl}chat/stream'))
          ..headers.addAll({
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
          })
          ..body = jsonEncode(body);
    final response = await client.send(request);
    if (response.statusCode != 200) {
      throw Exception(
        'La conversación no está disponible (${response.statusCode}). Inicia sesión o inténtalo nuevamente.',
      );
    }
    yield* response.stream;
  } finally {
    client.close();
  }
}

void downloadBytes(Uint8List bytes, String filename, String mime) {
  final blob = web.Blob([bytes.toJS].toJS, web.BlobPropertyBag(type: mime));
  final url = web.URL.createObjectURL(blob);
  final anchor = web.HTMLAnchorElement()
    ..href = url
    ..download = filename;
  anchor.click();
  Timer(const Duration(seconds: 10), () => web.URL.revokeObjectURL(url));
}

Future<Uint8List?> pickWorkbook() async {
  final picker = web.HTMLInputElement()
    ..type = 'file'
    ..accept = '.xlsx';
  final completer = Completer<Uint8List?>();
  picker.onchange = ((web.Event event) {
    final file = picker.files?.item(0);
    if (file == null) {
      completer.complete(null);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      completer.completeError('El archivo supera 20 MB.');
      return;
    }
    file.arrayBuffer().toDart.then(
      (buffer) => completer.complete(buffer.toDart.asUint8List()),
    );
  }).toJS;
  picker.oncancel = ((web.Event event) => completer.complete(null)).toJS;
  picker.click();
  return completer.future;
}

/// Per-browser UI preferences; storage may be blocked in private windows.
String? readSetting(String key) {
  try {
    return web.window.localStorage.getItem(key);
  } catch (_) {
    return null;
  }
}

void writeSetting(String key, String value) {
  try {
    web.window.localStorage.setItem(key, value);
  } catch (_) {
    // The preference simply lasts for this session.
  }
}

/// Opens the system share sheet (WhatsApp, correo…) with a file. Returns false
/// when the browser cannot share files, so the caller downloads it instead.
Future<bool> shareBytes(
  Uint8List bytes,
  String filename,
  String mime,
  String title,
) async {
  final file = web.File(
    [bytes.toJS].toJS,
    filename,
    web.FilePropertyBag(type: mime),
  );
  final data = web.ShareData(title: title, text: title, files: [file].toJS);
  try {
    if (!web.window.navigator.canShare(data)) return false;
  } catch (_) {
    return false; // canShare is missing in some desktop browsers.
  }
  try {
    await web.window.navigator.share(data).toDart;
    return true;
  } catch (error) {
    // Closing the share sheet is a choice, not a failure.
    return error.toString().contains('AbortError');
  }
}
