import 'package:flutter/material.dart';
import '../services/api_service.dart';

class FridgeScreen extends StatefulWidget {
  const FridgeScreen({super.key, required this.userId});

  final int userId;

  @override
  State<FridgeScreen> createState() => _FridgeScreenState();
}

class _FridgeScreenState extends State<FridgeScreen> {
  final ApiService _api = ApiService();
  List<dynamic> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final items = await _api.getFridge(widget.userId);
    setState(() {
      _items = items;
      _loading = false;
    });
  }

  Color _expiryColor(double score) {
    if (score >= 0.9) return Colors.red;
    if (score >= 0.7) return Colors.orange;
    return Colors.green;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Fridge Inventory')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: _items.length,
              itemBuilder: (_, i) {
                final item = _items[i] as Map<String, dynamic>;
                final priority = (item['expiry_priority_score'] as num?)?.toDouble() ?? 0;
                return ListTile(
                  leading: CircleAvatar(
                    backgroundColor: _expiryColor(priority),
                    child: Text('${item['days_to_expiry']}d'),
                  ),
                  title: Text('${item['ingredient_name']}'),
                  subtitle: Text(
                    '${item['quantity']} ${item['unit']} · ${item['storage_type']}\n'
                    'Expires: ${item['expiry_date']}',
                  ),
                  isThreeLine: true,
                );
              },
            ),
    );
  }
}
