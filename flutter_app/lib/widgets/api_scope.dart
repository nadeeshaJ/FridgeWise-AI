import 'package:flutter/material.dart';

import '../services/api_config.dart';
import '../services/api_service.dart';

/// Provides a shared [ApiService] that respects saved API URL settings.
class ApiScope extends InheritedWidget {
  const ApiScope({
    super.key,
    required this.config,
    required this.api,
    required super.child,
  });

  final ApiConfig config;
  final ApiService api;

  static ApiScope of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<ApiScope>();
    assert(scope != null, 'ApiScope not found in widget tree');
    return scope!;
  }

  static ApiService apiOf(BuildContext context) => of(context).api;

  @override
  bool updateShouldNotify(ApiScope oldWidget) =>
      oldWidget.config.baseUrl != config.baseUrl;
}
