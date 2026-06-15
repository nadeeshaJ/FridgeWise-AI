# Generate Flutter platform folders and apply dev permissions.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$AppDir = Join-Path $Root "flutter_app"

function Get-FlutterCmd {
    if (Get-Command flutter -ErrorAction SilentlyContinue) {
        return "flutter"
    }
    $Local = Join-Path $Root ".flutter-sdk\bin\flutter.bat"
    if (Test-Path $Local) {
        return $Local
    }
    Write-Host "Flutter not found. Cloning stable SDK to .flutter-sdk ..."
    git clone --depth 1 -b stable https://github.com/flutter/flutter.git (Join-Path $Root ".flutter-sdk")
    return $Local
}

$Flutter = Get-FlutterCmd
Push-Location $AppDir
try {
    & $Flutter create . --project-name fridge_wise_app --org com.fridgewise
    & $Flutter pub get

    $Manifest = Join-Path $AppDir "android\app\src\main\AndroidManifest.xml"
    if (Test-Path $Manifest) {
        @"
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.CAMERA"/>
    <application
        android:label="fridge_wise_app"
        android:name="`${applicationName}"
        android:icon="@mipmap/ic_launcher"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTop"
            android:taskAffinity=""
            android:theme="@style/LaunchTheme"
            android:configChanges="orientation|keyboardHidden|keyboard|screenSize|smallestScreenSize|locale|layoutDirection|fontScale|screenLayout|density|uiMode"
            android:hardwareAccelerated="true"
            android:windowSoftInputMode="adjustResize">
            <meta-data
              android:name="io.flutter.embedding.android.NormalTheme"
              android:resource="@style/NormalTheme"
              />
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
        <meta-data
            android:name="flutterEmbedding"
            android:value="2" />
    </application>
    <queries>
        <intent>
            <action android:name="android.intent.action.PROCESS_TEXT"/>
            <data android:mimeType="text/plain"/>
        </intent>
    </queries>
</manifest>
"@ | Set-Content $Manifest -Encoding utf8
        Write-Host "Wrote AndroidManifest.xml with HTTP + camera permissions"
    }

    Write-Host ""
    Write-Host "Setup complete. Run:"
    Write-Host "  cd flutter_app"
    Write-Host "  flutter run"
}
finally {
    Pop-Location
}
