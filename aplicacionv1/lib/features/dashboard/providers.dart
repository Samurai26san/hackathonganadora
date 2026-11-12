import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/api/api_client.dart';
import '../../core/api/models.dart';

final filtersProvider = StateProvider<BudgetFilters>(
  (ref) => const BudgetFilters(),
);
final catalogsProvider = FutureProvider<Catalogs>(
  (ref) => ref.watch(apiProvider).catalogs(),
);
final reportProvider = FutureProvider.autoDispose
    .family<FinancialReport, String>(
      (ref, type) =>
          ref.watch(apiProvider).report(type, ref.watch(filtersProvider)),
    );

final financialRevisionProvider = StreamProvider.autoDispose<int>((ref) {
  final api = ref.read(apiProvider);
  final controller = StreamController<int>();
  Timer? timer;
  Future<void> poll() async {
    try {
      final data = await api.get('data/revision') as Json;
      if (!controller.isClosed) controller.add(data['revision'] as int);
    } catch (_) {
      // A temporary outage must not discard an already displayed report.
    }
    // A cancellable timer, so disposal never leaves a pending poll behind.
    if (!controller.isClosed) {
      timer = Timer(const Duration(seconds: 10), poll);
    }
  }

  poll();
  ref.onDispose(() {
    timer?.cancel();
    controller.close();
  });
  return controller.stream;
});
