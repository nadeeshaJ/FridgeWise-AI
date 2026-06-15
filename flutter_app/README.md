# FridgeWise Flutter setup and demo helpers

## setup_flutter.ps1

Generates Android/iOS platform folders and applies HTTP + camera permissions for local API dev.

```powershell
.\scripts\setup_flutter.ps1
```

Requires Flutter SDK on PATH, or clones a local SDK to `.flutter-sdk/` automatically.

## run_demo.ps1

Starts the FastAPI backend bound to all interfaces (for physical devices on the same Wi‑Fi).

```powershell
.\scripts\run_demo.ps1
```

Then open the Flutter app → Settings (gear icon) → choose **Physical device (LAN)** and enter your PC IPv4 address from `ipconfig`.
