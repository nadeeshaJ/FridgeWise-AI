import 'package:flutter/material.dart';

import '../services/api_config.dart';
import '../services/api_service.dart';
import '../widgets/api_scope.dart';

Future<void> showApiSettingsSheet(BuildContext context) async {
  final scope = ApiScope.of(context);
  final controller = TextEditingController(text: scope.config.baseUrl);
  String? testMessage;
  bool testing = false;

  await showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (ctx) {
      return StatefulBuilder(
        builder: (ctx, setSheetState) {
          Future<void> testConnection() async {
            setSheetState(() {
              testing = true;
              testMessage = null;
            });
            try {
              final url = ApiConfig.normalizeBaseUrl(controller.text);
              await ApiService(baseUrl: url).checkHealth();
              setSheetState(() {
                testMessage = 'Connected to $url';
                testing = false;
              });
            } catch (e) {
              setSheetState(() {
                testMessage = e.toString();
                testing = false;
              });
            }
          }

          return Padding(
            padding: EdgeInsets.only(
              left: 16,
              right: 16,
              top: 8,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('API server', style: Theme.of(ctx).textTheme.titleLarge),
                const SizedBox(height: 8),
                const Text(
                  'For a physical phone, use your PC LAN IP (run ipconfig on Windows). '
                  'Start the backend with: python api/main.py',
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: ApiConfig.presets.entries.map((entry) {
                    return ActionChip(
                      label: Text(entry.key),
                      onPressed: () {
                        controller.text = entry.value;
                        setSheetState(() => testMessage = null);
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: controller,
                  decoration: const InputDecoration(
                    labelText: 'Base URL',
                    hintText: 'http://192.168.1.100:8000',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.url,
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: testing ? null : testConnection,
                        icon: testing
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.link),
                        label: const Text('Test connection'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: () async {
                          final url = ApiConfig.normalizeBaseUrl(controller.text);
                          await scope.config.saveBaseUrl(url);
                          if (ctx.mounted) Navigator.pop(ctx, url);
                        },
                        child: const Text('Save'),
                      ),
                    ),
                  ],
                ),
                if (testMessage != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    testMessage!,
                    style: TextStyle(
                      color: testMessage!.startsWith('Connected')
                          ? Colors.green.shade700
                          : Colors.red.shade700,
                    ),
                  ),
                ],
              ],
            ),
          );
        },
      );
    },
  );
}
