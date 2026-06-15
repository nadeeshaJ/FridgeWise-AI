import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import 'api_config.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class ApiService {
  ApiService({String? baseUrl})
      : baseUrl = ApiConfig.normalizeBaseUrl(baseUrl ?? ApiConfig.platformDefault());

  final String baseUrl;

  static String defaultBaseUrl() => ApiConfig.platformDefault();

  Future<void> checkHealth() async {
    await _get('/health');
  }

  Future<List<dynamic>> getDemoUsers() async {
    final data = await _get('/demo-users') as Map<String, dynamic>;
    return data['users'] as List<dynamic>;
  }

  Future<List<dynamic>> getFridge(int userId) async {
    return await _get('/users/$userId/fridge') as List<dynamic>;
  }

  Future<Map<String, dynamic>> addFridgeItem(
    int userId, {
    required String ingredientName,
    double quantity = 1.0,
    String unit = 'piece',
    String storageType = 'fridge',
    int daysToExpiry = 7,
    String barcode = '',
  }) async {
    return await _post('/users/$userId/fridge/items', {
      'ingredient_name': ingredientName,
      'quantity': quantity,
      'unit': unit,
      'storage_type': storageType,
      'days_to_expiry': daysToExpiry,
      'barcode': barcode,
    }) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateFridgeItem(
    int userId,
    int inventoryId, {
    String? ingredientName,
    double? quantity,
    String? unit,
    String? storageType,
    int? daysToExpiry,
  }) async {
    final body = <String, dynamic>{};
    if (ingredientName != null) body['ingredient_name'] = ingredientName;
    if (quantity != null) body['quantity'] = quantity;
    if (unit != null) body['unit'] = unit;
    if (storageType != null) body['storage_type'] = storageType;
    if (daysToExpiry != null) body['days_to_expiry'] = daysToExpiry;
    return await _put('/users/$userId/fridge/items/$inventoryId', body)
        as Map<String, dynamic>;
  }

  Future<void> deleteFridgeItem(int userId, int inventoryId) async {
    await _delete('/users/$userId/fridge/items/$inventoryId');
  }

  Future<Map<String, dynamic>> addFridgeItemFromBarcode(
    int userId, {
    required String barcode,
    double quantity = 1.0,
    String unit = 'piece',
    String storageType = 'fridge',
    int daysToExpiry = 7,
  }) async {
    return await _post('/users/$userId/fridge/from-barcode', {
      'barcode': barcode,
      'quantity': quantity,
      'unit': unit,
      'storage_type': storageType,
      'days_to_expiry': daysToExpiry,
    }) as Map<String, dynamic>;
  }

  Future<List<dynamic>> getRecommendations(int userId, {int topK = 10}) async {
    return await _get('/users/$userId/recommendations?top_k=$topK') as List<dynamic>;
  }

  Future<Map<String, dynamic>> getRecipe(int recipeId) async {
    return await _get('/recipes/$recipeId') as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getProduct(String barcode) async {
    return await _get('/products/$barcode') as Map<String, dynamic>;
  }

  Future<dynamic> _get(String path) async {
    try {
      final res = await http.get(Uri.parse('$baseUrl$path'));
      return _decode(res);
    } on SocketException {
      throw ApiException(
        'Cannot reach the API at $baseUrl. Start the backend with: python api/main.py',
      );
    }
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl$path'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );
      return _decode(res);
    } on SocketException {
      throw ApiException(
        'Cannot reach the API at $baseUrl. Start the backend with: python api/main.py',
      );
    }
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    try {
      final res = await http.put(
        Uri.parse('$baseUrl$path'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );
      return _decode(res);
    } on SocketException {
      throw ApiException(
        'Cannot reach the API at $baseUrl. Start the backend with: python api/main.py',
      );
    }
  }

  Future<void> _delete(String path) async {
    try {
      final res = await http.delete(Uri.parse('$baseUrl$path'));
      if (res.statusCode == 204) return;
      _decode(res);
    } on SocketException {
      throw ApiException(
        'Cannot reach the API at $baseUrl. Start the backend with: python api/main.py',
      );
    }
  }

  dynamic _decode(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      if (res.body.isEmpty) return null;
      return json.decode(res.body);
    }
    String message;
    try {
      final body = json.decode(res.body);
      if (body is Map && body['detail'] != null) {
        message = body['detail'].toString();
      } else {
        message = res.body;
      }
    } catch (_) {
      message = res.body.isNotEmpty ? res.body : 'Request failed (${res.statusCode})';
    }
    throw ApiException(message, statusCode: res.statusCode);
  }
}
