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

final financialRevisionProvider = StreamProvider.autoDispose<int>((ref) async* {
  final api = ref.read(apiProvider);
  var active = true;
  ref.onDispose(() => active = false);
  while (active) {
    try {
      final data = await api.get('data/revision') as Json;
      if (active) yield data['revision'] as int;
    } catch (_) {
      // A temporary outage must not discard an already displayed report.
    }
    await Future<void>.delayed(const Duration(seconds: 10));
  }
});
