import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';
import '../../core/auth/auth_controller.dart';
import '../../shared/widgets/juku_mascot.dart';
import '../../core/theme/theme_mode.dart';
import '../../core/theme/app_theme.dart';

final serverConfigProvider = FutureProvider<Json>(
  (ref) async => await ref.read(apiProvider).get('/health') as Json,
);

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final email = TextEditingController(), password = TextEditingController();
  final form = GlobalKey<FormState>();
  bool hidden = true, busy = false;
  String? error;
  @override
  void dispose() {
    email.dispose();
    password.dispose();
    super.dispose();
  }

  Future<void> submit(bool demo) async {
    if (demo && !form.currentState!.validate()) return;
    setState(() {
      busy = true;
      error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(email.text.trim(), password.text);
    } catch (value) {
      if (mounted) setState(() => error = '$value');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final config = ref.watch(serverConfigProvider);
    final demo = config.valueOrNull?['auth_mode'] == 'demo';
    final story = Container(
      color: ExbColors.story,
      padding: const EdgeInsets.all(48),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Image.asset(
            'assets/images/logo-ensena-bolivia.png',
            width: 220,
            semanticLabel: 'Enseña por Bolivia',
          ),
          const SizedBox(height: 64),
          Text(
            'TU ASISTENTE EN EL SISTEMA',
            style: TextStyle(
              color: ExbColors.green,
              fontSize: 11,
              fontWeight: FontWeight.w700,
              letterSpacing: 2,
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            '¡Hola, soy\nJUKU!',
            style: TextStyle(
              fontSize: 64,
              fontWeight: FontWeight.w700,
              letterSpacing: -3,
              height: 1.04,
            ),
          ),
          const SizedBox(height: 20),
          SizedBox(
            width: 360,
            child: Text(
              'Te acompaño a entender y explorar la información de Enseña por Bolivia.',
              style: TextStyle(
                fontSize: 17,
                height: 1.7,
                color: ExbColors.secondaryText,
              ),
            ),
          ),
          const SizedBox(height: 28),
          for (final label in [
            'Encuentra presupuestos y movimientos.',
            'Abre reportes con los filtros que necesitas.',
            'Entiende los indicadores y consulta su detalle.',
          ])
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(
                    Icons.check_circle_outline,
                    size: 18,
                    color: ExbColors.green,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      label,
                      style: TextStyle(fontSize: 13, color: ExbColors.green),
                    ),
                  ),
                ],
              ),
            ),
          Align(
            alignment: Alignment.centerRight,
            child: const JukuMascot(JukuPose.saludo, size: 230),
          ),
          Text(
            'JUKU · Aquí para acompañarte',
            style: TextStyle(fontSize: 12, color: ExbColors.green),
          ),
        ],
      ),
    );
    final login = Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 430),
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Form(
            key: form,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: ExbColors.story,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    demo
                        ? 'DEMO LOCAL · DATOS DEL EXCEL'
                        : 'ACCESO INSTITUCIONAL',
                    style: TextStyle(
                      fontSize: 10,
                      letterSpacing: 1,
                      color: ExbColors.green,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Bienvenido a\nExB Finanzas',
                  style: TextStyle(
                    fontSize: 36,
                    height: 1.15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: -1.2,
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  'Sistema de control presupuestario',
                  style: TextStyle(
                    color: ExbColors.secondaryText,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 32),
                if (demo) ...[
                  TextFormField(
                    controller: email,
                    decoration: const InputDecoration(
                      labelText: 'Correo electrónico',
                      hintText: 'tu.correo@institucion.org',
                    ),
                    keyboardType: TextInputType.emailAddress,
                    autofillHints: const [AutofillHints.username],
                    validator: (value) => value == null || !value.contains('@')
                        ? 'Ingresa un correo válido.'
                        : null,
                  ),
                  const SizedBox(height: 20),
                  TextFormField(
                    controller: password,
                    obscureText: hidden,
                    autofillHints: const [AutofillHints.password],
                    decoration: InputDecoration(
                      labelText: 'Contraseña',
                      suffixIcon: IconButton(
                        tooltip: hidden
                            ? 'Mostrar contraseña'
                            : 'Ocultar contraseña',
                        onPressed: () => setState(() => hidden = !hidden),
                        icon: Icon(
                          hidden
                              ? Icons.visibility_outlined
                              : Icons.visibility_off_outlined,
                          size: 20,
                        ),
                      ),
                    ),
                    validator: (value) => value == null || value.isEmpty
                        ? 'Ingresa tu contraseña.'
                        : null,
                    onFieldSubmitted: (_) => submit(demo),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'El rol se asigna automáticamente según tu cuenta.',
                    style: TextStyle(
                      fontSize: 11,
                      color: ExbColors.secondaryText,
                    ),
                  ),
                  const SizedBox(height: 22),
                ] else
                  Padding(
                    padding: EdgeInsets.only(bottom: 22),
                    child: Text(
                      'Ingresa con tu cuenta institucional mediante el proveedor autorizado. Tus credenciales permanecen en su página de acceso.',
                      style: TextStyle(
                        height: 1.7,
                        color: ExbColors.secondaryText,
                      ),
                    ),
                  ),
                if (config.hasError || error != null)
                  Semantics(
                    liveRegion: true,
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(
                        error ??
                            'El servidor no está disponible. Verifica la configuración de la API.',
                        style: TextStyle(color: ExbColors.amber, height: 1.5),
                      ),
                    ),
                  ),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: busy || config.isLoading
                        ? null
                        : () => submit(demo),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        if (busy)
                          const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        if (busy) const SizedBox(width: 10),
                        Text(
                          demo
                              ? 'Ingresar al sistema'
                              : 'Iniciar sesión institucional',
                        ),
                        const SizedBox(width: 12),
                        const Icon(Icons.north_east, size: 18),
                      ],
                    ),
                  ),
                ),
                if (demo) ...[
                  const SizedBox(height: 28),
                  const Divider(),
                  const SizedBox(height: 16),
                  const Text(
                    'Prueba la experiencia',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Completa el formulario con una cuenta local.',
                    style: TextStyle(
                      fontSize: 12,
                      color: ExbColors.secondaryText,
                    ),
                  ),
                  const SizedBox(height: 14),
                  for (final account in [
                    ('Técnico', 'tecnico@exb.demo', 'Consultar y exportar'),
                    (
                      'Administrador',
                      'admin@exb.demo',
                      'Gestionar información',
                    ),
                  ])
                    Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: SizedBox(
                        width: double.infinity,
                        child: OutlinedButton(
                          onPressed: () {
                            email.text = account.$2;
                            password.text = 'Demo2026!';
                          },
                          child: Row(
                            children: [
                              Expanded(child: Text(account.$1)),
                              const SizedBox(width: 8),
                              Flexible(
                                child: Text(
                                  '${account.$3} →',
                                  textAlign: TextAlign.right,
                                  style: const TextStyle(fontSize: 11),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  Text(
                    'Contraseña local: Demo2026!\nModo de demostración. No ingreses credenciales reales.',
                    style: TextStyle(
                      fontSize: 10,
                      height: 1.6,
                      color: ExbColors.secondaryText,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
    return Scaffold(
      floatingActionButtonLocation: FloatingActionButtonLocation.endTop,
      floatingActionButton: MediaQuery.sizeOf(context).width >= 900
          ? const ThemeToggle()
          : null,
      body: LayoutBuilder(
        builder: (context, constraints) => SingleChildScrollView(
          child: constraints.maxWidth >= 900
              ? IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: ConstrainedBox(
                          constraints: BoxConstraints(
                            minHeight: constraints.maxHeight,
                          ),
                          child: story,
                        ),
                      ),
                      Expanded(child: login),
                    ],
                  ),
                )
              : Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(24),
                      child: Row(
                        children: [
                          Image.asset(
                            'assets/images/logo-ensena-bolivia.png',
                            width: 160,
                          ),
                          const Spacer(),
                          const ThemeToggle(),
                          const JukuMascot(JukuPose.saludo, size: 84),
                        ],
                      ),
                    ),
                    login,
                  ],
                ),
        ),
      ),
    );
  }
}
