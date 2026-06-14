import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/error_view.dart';

class RecipeDetailScreen extends StatefulWidget {
  const RecipeDetailScreen({
    super.key,
    required this.recipeId,
    required this.recommendation,
  });

  final int recipeId;
  final Map<String, dynamic> recommendation;

  @override
  State<RecipeDetailScreen> createState() => _RecipeDetailScreenState();
}

class _RecipeDetailScreenState extends State<RecipeDetailScreen> {
  final ApiService _api = ApiService();
  Map<String, dynamic>? _recipe;
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
      final recipe = await _api.getRecipe(widget.recipeId);
      if (!mounted) return;
      setState(() {
        _recipe = recipe;
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
    final rec = widget.recommendation;
    return Scaffold(
      appBar: AppBar(title: Text('${rec['recipe_name']}')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Why recommended',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        'Uses expiring ingredients: ${rec['matched_ingredients'] ?? 'n/a'}\n'
                        'Missing: ${rec['missing_ingredients'] ?? 'none'}\n'
                        'Nutrition score: ${rec['nutrition_score']}',
                      ),
                      const Divider(height: 32),
                      Text('Ingredients', style: Theme.of(context).textTheme.titleMedium),
                      Text('${_recipe?['ingredients'] ?? ''}'),
                      const SizedBox(height: 16),
                      Text('Steps', style: Theme.of(context).textTheme.titleMedium),
                      Text('${_recipe?['steps'] ?? ''}'),
                      const SizedBox(height: 16),
                      Text('Cooking time: ${_recipe?['minutes'] ?? rec['minutes']} minutes'),
                    ],
                  ),
                ),
    );
  }
}
