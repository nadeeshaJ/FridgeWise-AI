import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  ApiService({this.baseUrl = 'http://10.0.2.2:8000'});

  final String baseUrl;

  Future<List<dynamic>> getDemoUsers() async {
    final res = await http.get(Uri.parse('$baseUrl/demo-users'));
    if (res.statusCode != 200) throw Exception('Failed to load demo users');
    final data = json.decode(res.body) as Map<String, dynamic>;
    return data['users'] as List<dynamic>;
  }

  Future<List<dynamic>> getFridge(int userId) async {
    final res = await http.get(Uri.parse('$baseUrl/users/$userId/fridge'));
    if (res.statusCode != 200) throw Exception('Fridge not found for user $userId');
    return json.decode(res.body) as List<dynamic>;
  }

  Future<List<dynamic>> getRecommendations(int userId, {int topK = 10}) async {
    final res = await http.get(
      Uri.parse('$baseUrl/users/$userId/recommendations?top_k=$topK'),
    );
    if (res.statusCode != 200) {
      throw Exception('No recommendations for user $userId');
    }
    return json.decode(res.body) as List<dynamic>;
  }

  Future<Map<String, dynamic>> getRecipe(int recipeId) async {
    final res = await http.get(Uri.parse('$baseUrl/recipes/$recipeId'));
    if (res.statusCode != 200) throw Exception('Recipe $recipeId not found');
    return json.decode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> getProduct(String barcode) async {
    final res = await http.get(Uri.parse('$baseUrl/products/$barcode'));
    if (res.statusCode != 200) throw Exception('Product $barcode not found');
    return json.decode(res.body) as Map<String, dynamic>;
  }
}
