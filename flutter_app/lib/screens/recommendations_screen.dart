import 'package:flutter/material.dart';

import '../widgets/api_scope.dart';
import '../widgets/error_view.dart';
import 'recipe_detail_screen.dart';

class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({super.key, required this.userId});

  final int userId;

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  List<dynamic> _recs = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final recs = await ApiScope.apiOf(context).getRecommendations(widget.userId);
      if (!mounted) return;
      setState(() {
        _recs = recs;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = friendlyError(e);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Recommended Recipes'),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.builder(
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
                ),
    );
  }
}
