import 'package:flutter/material.dart';

import '../widgets/api_scope.dart';
import '../widgets/api_settings_sheet.dart';
import '../widgets/error_view.dart' show friendlyError;
import 'barcode_screen.dart';
import 'fridge_screen.dart';
import 'recommendations_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.onApiSettingsChanged});

  final VoidCallback onApiSettingsChanged;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<dynamic> _users = [];
  int? _selectedUser;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadUsers();
  }

  Future<void> _loadUsers() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ApiScope.apiOf(context);
      final users = await api.getDemoUsers();
      if (!mounted) return;
      setState(() {
        _users = users;
        _selectedUser = users.isNotEmpty ? users.first as int : null;
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

  Future<void> _openApiSettings() async {
    await showApiSettingsSheet(context);
    widget.onApiSettingsChanged();
    if (mounted) _loadUsers();
  }

  @override
  Widget build(BuildContext context) {
    final apiUrl = ApiScope.of(context).config.baseUrl;

    if (_loading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('FridgeWise AI'),
          actions: [
            IconButton(
              onPressed: _openApiSettings,
              icon: const Icon(Icons.settings),
              tooltip: 'API settings',
            ),
          ],
        ),
        body: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.cloud_off, size: 48),
              const SizedBox(height: 16),
              Text(
                'Cannot reach API at:\n$apiUrl',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 8),
              Text(_error!, style: TextStyle(color: Colors.red.shade700)),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _loadUsers,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
              const SizedBox(height: 8),
              OutlinedButton.icon(
                onPressed: _openApiSettings,
                icon: const Icon(Icons.settings),
                label: const Text('Change API URL'),
              ),
            ],
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('FridgeWise AI'),
        backgroundColor: Colors.green.shade700,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            onPressed: _openApiSettings,
            icon: const Icon(Icons.settings),
            tooltip: 'API settings',
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              color: Colors.green.shade50,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Text(
                  'Demo users use cold-start mode — recommendations are based on '
                  'fridge contents, expiry, and nutrition (no Food.com rating history).',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Text('Demo user', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            DropdownButtonFormField<int>(
              value: _selectedUser,
              items: _users
                  .map((u) => DropdownMenuItem(value: u as int, child: Text('User $u')))
                  .toList(),
              onChanged: (v) => setState(() => _selectedUser = v),
            ),
            const SizedBox(height: 8),
            Text(
              'API: $apiUrl',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey.shade700),
            ),
            const SizedBox(height: 16),
            _NavCard(
              icon: Icons.kitchen,
              title: 'My Fridge',
              subtitle: 'View, add, edit, and delete ingredients',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => FridgeScreen(userId: _selectedUser!)),
              ),
            ),
            _NavCard(
              icon: Icons.restaurant_menu,
              title: 'Recipe Recommendations',
              subtitle: 'Hybrid recommender with match % and expiring items',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RecommendationsScreen(userId: _selectedUser!),
                ),
              ),
            ),
            _NavCard(
              icon: Icons.qr_code_scanner,
              title: 'Barcode / Nutrition',
              subtitle: 'Scan or enter a barcode, add to fridge',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => BarcodeScreen(userId: _selectedUser!),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NavCard extends StatelessWidget {
  const _NavCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: Icon(icon, color: Colors.green.shade700),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(subtitle),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
