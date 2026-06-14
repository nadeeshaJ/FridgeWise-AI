import 'package:flutter/material.dart';
import '../services/api_service.dart';

class BarcodeScreen extends StatefulWidget {
  const BarcodeScreen({super.key});

  @override
  State<BarcodeScreen> createState() => _BarcodeScreenState();
}

class _BarcodeScreenState extends State<BarcodeScreen> {
  final ApiService _api = ApiService();
  final _controller = TextEditingController(text: '8000500310427');
  Map<String, dynamic>? _product;
  String? _error;
  bool _loading = false;

  Future<void> _lookup() async {
    setState(() {
      _loading = true;
      _error = null;
      _product = null;
    });
    try {
      final product = await _api.getProduct(_controller.text.trim());
      setState(() => _product = product);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Barcode / Nutrition')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: 'Barcode',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 12),
            FilledButton(onPressed: _loading ? null : _lookup, child: const Text('Look up')),
            const SizedBox(height: 24),
            if (_loading) const Center(child: CircularProgressIndicator()),
            if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
            if (_product != null) ...[
              Text(_product!['product_name'] ?? '',
                  style: Theme.of(context).textTheme.titleLarge),
              Text('Brand: ${_product!['brand']}'),
              Text('Ingredient: ${_product!['generic_ingredient_name']}'),
              Text('Nutri-Score: ${_product!['nutriscore_grade']}'),
              Text('Allergens: ${_product!['allergens']}'),
              const SizedBox(height: 8),
              Text(
                'Per 100g: ${_product!['energy_kcal_100g']} kcal, '
                'protein ${_product!['protein_100g']}g, '
                'sugars ${_product!['sugars_100g']}g',
              ),
            ],
          ],
        ),
      ),
    );
  }
}
