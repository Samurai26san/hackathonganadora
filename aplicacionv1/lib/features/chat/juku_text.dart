import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// Minimal formatting for Juku answers: **negrita**, viñetas "- " y
/// líneas _en cursiva_. The backend writes only this subset.
class JukuText extends StatelessWidget {
  const JukuText(this.text, {super.key});
  final String text;

  static TextStyle get _base =>
      TextStyle(fontSize: 13, height: 1.55, color: ExbColors.dark);

  static List<TextSpan> _inline(String line, TextStyle style) {
    final spans = <TextSpan>[];
    final bold = RegExp(r'\*\*(.+?)\*\*');
    var start = 0;
    for (final match in bold.allMatches(line)) {
      if (match.start > start) {
        spans.add(TextSpan(text: line.substring(start, match.start)));
      }
      spans.add(
        TextSpan(
          text: match.group(1),
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
      );
      start = match.end;
    }
    if (start < line.length) spans.add(TextSpan(text: line.substring(start)));
    return [TextSpan(style: style, children: spans)];
  }

  @override
  Widget build(BuildContext context) {
    final children = <Widget>[];
    for (final raw in text.trim().split('\n')) {
      final line = raw.trimRight();
      if (line.isEmpty) {
        children.add(const SizedBox(height: 8));
      } else if (line.startsWith('- ')) {
        children.add(
          Padding(
            padding: const EdgeInsets.only(left: 4, bottom: 2),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: EdgeInsets.only(top: 8, right: 8),
                  child: CircleAvatar(
                    radius: 2.5,
                    backgroundColor: ExbColors.execution,
                  ),
                ),
                Expanded(
                  child: Text.rich(
                    TextSpan(children: _inline(line.substring(2), _base)),
                  ),
                ),
              ],
            ),
          ),
        );
      } else if (line.length > 2 &&
          line.startsWith('_') &&
          line.endsWith('_')) {
        children.add(
          Text(
            line.substring(1, line.length - 1),
            style: _base.copyWith(
              fontSize: 11,
              fontStyle: FontStyle.italic,
              color: ExbColors.secondaryText,
            ),
          ),
        );
      } else {
        children.add(Text.rich(TextSpan(children: _inline(line, _base))));
      }
    }
    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: children,
      ),
    );
  }
}
