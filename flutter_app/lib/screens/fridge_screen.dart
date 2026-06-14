import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../widgets/error_view.dart';

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
      final items = await _api.getFridge(widget.userId);
      if (!mounted) return;
      setState(() {
        _items = items;
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

  Future<void> _showItemDialog({Map<String, dynamic>? item}) async {
    final isEdit = item != null;
    final nameCtrl = TextEditingController(text: item?['ingredient_name']?.toString() ?? '');
    final qtyCtrl = TextEditingController(
      text: (item?['quantity'] as num?)?.toString() ?? '1',
    );
    final daysCtrl = TextEditingController(
      text: (item?['days_to_expiry'] as num?)?.toString() ?? '7',
    );
    var unit = item?['unit']?.toString() ?? 'piece';
    var storage = item?['storage_type']?.toString() ?? 'fridge';

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          title: Text(isEdit ? 'Edit item' : 'Add item'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Ingredient name',
                    border: OutlineInputBorder(),
                  ),
                  textCapitalization: TextCapitalization.sentences,
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: qtyCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Quantity',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: unit,
                  decoration: const InputDecoration(
                    labelText: 'Unit',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'piece', child: Text('piece')),
                    DropdownMenuItem(value: 'g', child: Text('g')),
                    DropdownMenuItem(value: 'cup', child: Text('cup')),
                    DropdownMenuItem(value: 'pack', child: Text('pack')),
                    DropdownMenuItem(value: 'bottle', child: Text('bottle')),
                  ],
                  onChanged: (v) => setDialogState(() => unit = v ?? unit),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  value: storage,
                  decoration: const InputDecoration(
                    labelText: 'Storage',
                    border: OutlineInputBorder(),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'fridge', child: Text('Fridge')),
                    DropdownMenuItem(value: 'freezer', child: Text('Freezer')),
                    DropdownMenuItem(value: 'pantry', child: Text('Pantry')),
                  ],
                  onChanged: (v) => setDialogState(() => storage = v ?? storage),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: daysCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Days until expiry',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.number,
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(isEdit ? 'Save' : 'Add')),
          ],
        ),
      ),
    );

    if (saved != true || !mounted) return;

    final name = nameCtrl.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Ingredient name is required')),
      );
      return;
    }

    final quantity = double.tryParse(qtyCtrl.text.trim()) ?? 1.0;
    final days = int.tryParse(daysCtrl.text.trim()) ?? 7;

    try {
      if (isEdit) {
        await _api.updateFridgeItem(
          widget.userId,
          item!['inventory_id'] as int,
          ingredientName: name,
          quantity: quantity,
          unit: unit,
          storageType: storage,
          daysToExpiry: days,
        );
      } else {
        await _api.addFridgeItem(
          widget.userId,
          ingredientName: name,
          quantity: quantity,
          unit: unit,
          storageType: storage,
          daysToExpiry: days,
        );
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(isEdit ? 'Item updated' : 'Item added')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(friendlyError(e))),
      );
    }
  }

  Future<void> _confirmDelete(Map<String, dynamic> item) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Remove item?'),
        content: Text('Remove ${item['ingredient_name']} from your fridge?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    try {
      await _api.deleteFridgeItem(widget.userId, item['inventory_id'] as int);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Item removed')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(friendlyError(e))),
      );
    }
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
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _error == null ? () => _showItemDialog() : null,
        icon: const Icon(Icons.add),
        label: const Text('Add item'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? ErrorView(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: _items.isEmpty
                      ? ListView(
                          children: const [
                            SizedBox(height: 120),
                            Icon(Icons.kitchen_outlined, size: 48, color: Colors.grey),
                            SizedBox(height: 16),
                            Center(child: Text('Your fridge is empty. Tap Add item to start.')),
                          ],
                        )
                      : ListView.builder(
                          itemCount: _items.length,
                          itemBuilder: (_, i) {
                            final item = _items[i] as Map<String, dynamic>;
                            final priority =
                                (item['expiry_priority_score'] as num?)?.toDouble() ?? 0;
                            return Dismissible(
                              key: ValueKey(item['inventory_id']),
                              direction: DismissDirection.endToStart,
                              background: Container(
                                color: Colors.red,
                                alignment: Alignment.centerRight,
                                padding: const EdgeInsets.only(right: 20),
                                child: const Icon(Icons.delete, color: Colors.white),
                              ),
                              confirmDismiss: (_) async {
                                await _confirmDelete(item);
                                return false;
                              },
                              child: ListTile(
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
                                onTap: () => _showItemDialog(item: item),
                                trailing: IconButton(
                                  icon: const Icon(Icons.delete_outline),
                                  onPressed: () => _confirmDelete(item),
                                ),
                              ),
                            );
                          },
                        ),
                ),
    );
  }
}
