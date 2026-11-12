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
