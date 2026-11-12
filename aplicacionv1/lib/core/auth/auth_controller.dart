import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../api/api_client.dart';
import '../api/models.dart';

final authProvider =
    StateNotifierProvider<AuthController, AsyncValue<AppUser?>>(
      (ref) => AuthController(ref.read(apiProvider)),
    );

class AuthController extends StateNotifier<AsyncValue<AppUser?>> {
  AuthController(this.api) : super(const AsyncLoading()) {
    restore();
  }
  final ApiClient api;
  Future<void> restore() async {
    try {
      state = AsyncData(await api.me());
    } catch (_) {
      state = const AsyncData(null);
    }
  }

  Future<void> login(String email, String password) async {
    final result =
        await api.post(
              'auth/login',
              data: {'email': email, 'password': password},
            )
            as Json;
    if (result['authorization_url'] != null) {
      if (!await launchUrl(
        Uri.parse(result['authorization_url'] as String),
        webOnlyWindowName: '_self',
      )) {
        throw const ApiError(
          'No se pudo abrir el inicio de sesión institucional.',
        );
      }
    } else {
      state = AsyncData(AppUser.fromJson(result));
    }
  }

  Future<void> logout() async {
    await api.post('auth/logout');
    state = const AsyncData(null);
  }
}
