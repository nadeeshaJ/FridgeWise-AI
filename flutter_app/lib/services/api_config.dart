import 'dart:io';

import 'package:shared_preferences/shared_preferences.dart';

/// Persists and resolves the FastAPI base URL for emulator vs physical device.
class ApiConfig {
  ApiConfig(this.baseUrl);

  static const prefsKey = 'api_base_url';

  String baseUrl;

  static String platformDefault() {
    if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    if (Platform.isIOS) return 'http://127.0.0.1:8000';
    return 'http://127.0.0.1:8000';
  }

  static Future<ApiConfig> load() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(prefsKey);
    return ApiConfig(normalizeBaseUrl(saved ?? platformDefault()));
  }

  Future<void> saveBaseUrl(String url) async {
    baseUrl = normalizeBaseUrl(url);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(prefsKey, baseUrl);
  }

  static String normalizeBaseUrl(String url) {
    var trimmed = url.trim();
    if (trimmed.isEmpty) return platformDefault();
    trimmed = trimmed.replaceAll(RegExp(r'/+$'), '');
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      trimmed = 'http://$trimmed';
    }
    return trimmed;
  }

  static const presets = <String, String>{
    'Android emulator': 'http://10.0.2.2:8000',
    'iOS simulator / desktop': 'http://127.0.0.1:8000',
    'Physical device (LAN)': 'http://192.168.1.100:8000',
  };
}
