/// Monetary arithmetic stays in integer cents. Doubles are only for geometry.
class Money implements Comparable<Money> {
  const Money(this.cents);
  final int cents;
  static const zero = Money(0);

  factory Money.parse(Object? value) {
    if (value == null) return zero;
    if (value is double) {
      throw const FormatException('Los importes deben recibirse como strings.');
    }
    final match = RegExp(r'^(-?)(\d+)(?:\.(\d+))?$').firstMatch('$value');
    if (match == null) throw FormatException('Importe inválido: $value');
    final fraction = (match[3] ?? '').padRight(3, '0');
    var cents =
        int.parse(match[2]!) * 100 + int.parse(fraction.substring(0, 2));
    if (int.parse(fraction[2]) >= 5) cents++;
    if (cents > 9007199254740991) {
      throw const FormatException(
        'Importe fuera del rango exacto de centavos del navegador.',
      );
    }
    return Money(match[1] == '-' ? -cents : cents);
  }

  Money operator +(Money other) => Money(cents + other.cents);
  Money operator -(Money other) => Money(cents - other.cents);
  @override
  int compareTo(Money other) => cents.compareTo(other.cents);
  String get decimal =>
      '${cents < 0 ? '-' : ''}${cents.abs() ~/ 100}.${(cents.abs() % 100).toString().padLeft(2, '0')}';
  String get formatted {
    final whole = '${cents.abs() ~/ 100}'.replaceAllMapped(
      RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
      (m) => '${m[1]}.',
    );
    return '${cents < 0 ? '−' : ''}$whole,${(cents.abs() % 100).toString().padLeft(2, '0')}';
  }

  String get currency => 'Bs $formatted';
}
