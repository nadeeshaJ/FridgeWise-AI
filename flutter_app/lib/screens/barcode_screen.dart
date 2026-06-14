import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../services/api_service.dart';
import '../widgets/error_view.dart';

class BarcodeScreen extends StatefulWidget {
  const BarcodeScreen({super.key, required this.userId});

  final int userId;

  @override
  State<BarcodeScreen> createState() => _BarcodeScreenState();
}

class _BarcodeScreenState extends State<BarcodeScreen> {
  final ApiService _api = ApiService();
  final _controller = TextEditingController(text: '8000500310427');
  Map<String, dynamic>? _product;
  String? _error;
  bool _loading = false;
  bool _scanning = false;
  MobileScannerController? _scannerController;

  @override
  void dispose() {
    _scannerController?.dispose();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _lookup() async {
    setState(() {
      _loading = true;
      _error = null;
      _product = null;
    });
    try {
      final product = await _api.getProduct(_controller.text.trim());
      if (!mounted) return;
      setState(() => _product = product);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addToFridge() async {
    if (_product == null) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await _api.addFridgeItemFromBarcode(
        widget.userId,
        barcode: _controller.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Added to fridge')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _toggleScanner() {
    setState(() {
      _scanning = !_scanning;
      if (_scanning) {
        _scannerController = MobileScannerController(
          detectionSpeed: DetectionSpeed.noDuplicates,
        );
      } else {
        _scannerController?.dispose();
        _scannerController = null;
      }
    });
  }

  void _onBarcodeDetected(BarcodeCapture capture) {
    final code = capture.barcodes.firstOrNull?.rawValue;
    if (code == null || code.isEmpty) return;
    _controller.text = code;
    _toggleScanner();
    _lookup();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Barcode / Nutrition')),
      body: ListView(
        padding: const EdgeInsets.all(16),
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
          Row(
            children: [
              Expanded(
                child: FilledButton(
                  onPressed: _loading ? null : _lookup,
                  child: const Text('Look up'),
                ),
              ),
              const SizedBox(width: 12),
              OutlinedButton.icon(
                onPressed: _toggleScanner,
                icon: Icon(_scanning ? Icons.close : Icons.qr_code_scanner),
                label: Text(_scanning ? 'Close' : 'Scan'),
              ),
            ],
          ),
          if (_scanning) ...[
            const SizedBox(height: 16),
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: SizedBox(
                height: 220,
                child: MobileScanner(
                  controller: _scannerController,
                  onDetect: _onBarcodeDetected,
                ),
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Point the camera at a product barcode. Lookup runs automatically.',
              style: TextStyle(color: Colors.grey),
            ),
          ],
          const SizedBox(height: 24),
          if (_loading) const Center(child: CircularProgressIndicator()),
          if (_error != null && !_loading)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Text(_error!, style: TextStyle(color: Colors.red.shade700)),
            ),
          if (_product != null) ...[
            Text(
              _product!['product_name']?.toString() ?? '',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
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
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _loading ? null : _addToFridge,
              icon: const Icon(Icons.add_shopping_cart),
              label: const Text('Add to fridge'),
            ),
          ],
        ],
      ),
    );
  }
}
