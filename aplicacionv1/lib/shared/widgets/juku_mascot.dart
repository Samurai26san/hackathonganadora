import 'package:flutter/material.dart';
import '../../core/theme/app_theme.dart';

/// Juku's illustrated poses (assets/juku), cut from the mascot sheet.
enum JukuPose {
  saludo('Juku saluda'),
  pensando('Juku está pensando'),
  senalando('Juku señala una opción'),
  celebrando('Juku celebra'),
  pdf('Juku con un informe PDF'),
  csv('Juku con una tabla CSV'),
  corriendo('Juku trabaja a toda velocidad');

  const JukuPose(this.label);
  final String label;
  String get asset => 'assets/juku/$name.png';
}

class JukuMascot extends StatelessWidget {
  const JukuMascot(this.pose, {super.key, this.size = 120, this.decorative});
  final JukuPose pose;
  final double size;

  /// Hide from screen readers when nearby text already says the same.
  final bool? decorative;

  @override
  Widget build(BuildContext context) {
    final image = Image.asset(
      pose.asset,
      width: size,
      height: size,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.medium,
      excludeFromSemantics: decorative ?? false,
      semanticLabel: decorative == true ? null : pose.label,
    );
    if (!ExbColors.night) return image;
    // The bear's dark fur needs a soft glow, as in the original artwork.
    return DecoratedBox(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: [
            ExbColors.glow.withValues(alpha: 0.22),
            ExbColors.glow.withValues(alpha: 0),
          ],
        ),
      ),
      child: image,
    );
  }
}
