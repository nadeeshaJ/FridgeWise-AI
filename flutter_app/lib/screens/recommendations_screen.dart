import 'package:flutter/material.dart';
import '../services/api_service.dart';
import 'recipe_detail_screen.dart';

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({super.key, required this.userId});

  final int userId;

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  final ApiService _api = ApiService();
  List<dynamic> _recs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final recs = await _api.getRecommendations(widget.userId);
    setState(() {
      _recs = recs;
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Recommended Recipes')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _recs.length,
              itemBuilder: (_, i) {
                final rec = _recs[i] as Map<String, dynamic>;
                final match = ((rec['ingredient_match_score'] as num?) ?? 0) * 100;
                return Card(
                  margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  child: ListTile(
                    title: Text('${rec['recipe_name']}'),
                    subtitle: Text(
                      'Match: ${match.toStringAsFixed(0)}% · '
                      'Expiry score: ${rec['expiry_priority_score']} · '
                      '${rec['minutes']} min',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => RecipeDetailScreen(
                          recipeId: rec['recipe_id'] as int,
                          recommendation: rec,
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
