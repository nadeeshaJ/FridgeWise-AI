import 'package:flutter/material.dart';

import 'services/api_config.dart';
import 'services/api_service.dart';
import 'screens/home_screen.dart';
import 'widgets/api_scope.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const FridgeWiseApp());
}

class FridgeWiseApp extends StatefulWidget {
  const FridgeWiseApp({super.key});

  @override
  State<FridgeWiseApp> createState() => _FridgeWiseAppState();
}

class _FridgeWiseAppState extends State<FridgeWiseApp> {
  late Future<ApiConfig> _configFuture = ApiConfig.load();

  void _reloadConfig() {
    setState(() {
      _configFuture = ApiConfig.load();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<ApiConfig>(
      future: _configFuture,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const MaterialApp(
            home: Scaffold(
              body: Center(child: CircularProgressIndicator()),
            ),
          );
        }

        final config = snapshot.data!;
        return ApiScope(
          config: config,
          api: ApiService(baseUrl: config.baseUrl),
          child: MaterialApp(
            title: 'FridgeWise AI',
            theme: ThemeData(
              colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
              useMaterial3: true,
            ),
            home: HomeScreen(onApiSettingsChanged: _reloadConfig),
          ),
        );
      },
    );
  }
}
