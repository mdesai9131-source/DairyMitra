import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mobile/main.dart';

void main() {
  testWidgets('DairyMitraApp initial render smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: DairyMitraApp(),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(find.byType(DairyMitraApp), findsOneWidget);
    // Settle splash navigation timer
    await tester.pump(const Duration(seconds: 3));
  });
}
