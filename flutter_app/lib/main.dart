import 'package:flutter/material.dart';
import 'screens/home_screen.dart';

void main() {
  runApp(const FridgeWiseApp());
}

class FridgeWiseApp extends StatelessWidget {
  const FridgeWiseApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FridgeWise AI',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
      ),
      home: const HomeScreen(),
    );
  }
}
