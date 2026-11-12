import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';

class JukuMessage {
  const JukuMessage({
    required this.role,
    this.text = '',
    this.report,
    this.citations = const [],
  });
  final String role, text;
  final FinancialReport? report;
  final List<Json> citations;
}

class JukuState {
  const JukuState({
    this.messages = const [],
    this.busy = false,
    this.status = '',
    this.sessionId,
    this.context,
    this.error,
  });
  final List<JukuMessage> messages;
  final bool busy;
  final String status;
  final String? sessionId, error;
  final Json? context;
}

final chatProvider = StateNotifierProvider<ChatController, JukuState>(
  (ref) => ChatController(ref.read(apiProvider)),
);

class ChatController extends StateNotifier<JukuState> {
  ChatController(this.api) : super(const JukuState());
  final ApiClient api;
  CancelToken? _cancel;

  void newSession() {
    _cancel?.cancel();
    state = const JukuState();
  }

  Future<void> loadSession(String id) async {
    _cancel?.cancel();
    state = JukuState(
      sessionId: id,
      busy: true,
      status: 'Recuperando conversación…',
    );
    try {
      final rows = await api.get('sessions/$id/messages') as List<dynamic>;
      final context = await api.get('sessions/$id/context') as Json;
      final messages = <JukuMessage>[];
      for (final dynamic row in rows) {
        if (row['role'] == 'tool' &&
            row['result'] is Map &&
            row['result']['summary'] != null) {
          messages.add(
            JukuMessage(
              role: 'assistant',
              report: FinancialReport.fromJson(row['result'] as Json),
            ),
          );
        } else if (row['content'] is String) {
          messages.add(
            JukuMessage(
              role: row['role'] as String,
              text: row['content'] as String,
            ),
          );
        }
      }
      state = JukuState(
        sessionId: id,
        messages: messages,
        context: context['active_filters'] as Json?,
      );
    } catch (error) {
      state = JukuState(sessionId: id, error: '$error');
    }
  }

  Future<void> send(String text, BudgetFilters filters) async {
    if (text.trim().isEmpty || state.busy) return;
    final cancel = CancelToken();
    _cancel = cancel;
    final messages = [...state.messages, JukuMessage(role: 'user', text: text)];
    var sessionId = state.sessionId;
    Json? context = state.context;
    state = JukuState(
      messages: messages,
      busy: true,
      status: 'Juku está revisando tu consulta…',
      sessionId: sessionId,
      context: context,
    );
    var finished = false;
    try {
      await for (final envelope in api.chat({
        'message': text,
        'session_id': sessionId,
        if (sessionId == null) 'filters': filters.toJson(),
      }, cancel)) {
        if (cancel.isCancelled) return;
        sessionId = envelope['session_id'] as String? ?? sessionId;
        final dynamic data = envelope['data'];
        var status = state.status;
        String? error;
        switch (envelope['event']) {
          case 'delta':
            if (data is String && data.isNotEmpty) {
              messages.add(JukuMessage(role: 'assistant', text: data));
            }
          case 'tool_call':
            status = data['name'] == 'search_institutional_knowledge'
                ? 'Buscando evidencia institucional…'
                : 'Consultando el motor financiero…';
          case 'tool_result':
            if (data['is_error'] == true) {
              error = data['result']['error'] as String?;
            } else if (data['result']['summary'] != null) {
              messages.add(
                JukuMessage(
                  role: 'assistant',
                  report: FinancialReport.fromJson(data['result'] as Json),
                ),
              );
            } else if (data['result']['citations'] is List) {
              messages.add(
                JukuMessage(
                  role: 'assistant',
                  citations: (data['result']['citations'] as List<dynamic>)
                      .cast<Json>(),
                ),
              );
            }
          case 'context_update':
            context = data['active_filters'] as Json;
          case 'done':
            finished = true;
            status = '';
          case 'error':
            finished = true;
            error = '$data';
            status = '';
        }
        state = JukuState(
          messages: [...messages],
          sessionId: sessionId,
          context: context,
          busy: !finished,
          status: status,
          error: error,
        );
      }
      if (!finished) {
        state = JukuState(
          messages: [...messages],
          sessionId: sessionId,
          context: context,
          error:
              'La conexión se interrumpió antes de completar la respuesta. Intenta nuevamente.',
        );
      }
    } catch (error) {
      if (!cancel.isCancelled) {
        state = JukuState(
          messages: [...messages],
          sessionId: sessionId,
          context: context,
          error: '$error',
        );
      }
    }
  }

  @override
  void dispose() {
    _cancel?.cancel();
    super.dispose();
  }
}
