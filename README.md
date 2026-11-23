# ZeroScope Fire TV Manager

A Python desktop application for managing your own Amazon Fire TV devices over your local network using Android Debug Bridge (ADB).

> **Project status:** Initial working GUI implementation. Network discovery, ADB connection, APK installation, package listing, and app uninstallation are implemented. Test against your own Fire TV hardware and firmware before relying on the results.

## Features

- **Device discovery:** Probe a user-supplied IPv4 subnet for devices accepting the configured ADB TCP port.
- **ADB connection:** Connect to a Fire TV by IP address and port.
- **Device status:** List ADB-connected devices and their authorization state.
- **APK installation:** Install an APK, with an optional reinstall/update flag.
- **Installed apps:** List third-party package names on a selected device.
- **Uninstall:** Uninstall a selected third-party package after confirmation.
- **Activity logs:** Show timestamped connection and app-management activity.
- **Settings:** Configure the ADB executable and default port.

## Technology

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Desktop GUI | PySide6 |
| Device communication | Android Debug Bridge (ADB) |
| Application format | Android `.apk` |
| Host environments | Linux, Ubuntu / WSL with WSLg, Windows with Python and ADB configured |

## Project structure

```text
FireTV-Manager/
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── main.py
│   ├── workers.py
│   └── services/
│       ├── __init__.py
│       └── adb.py
├── requirements.txt
└── README.md
```

## Requirements and packages

### System requirements

- Python 3.10 or newer
- Android SDK Platform-Tools (provides the `adb` executable)
- A supported graphical environment for PySide6 (WSLg for Ubuntu on Windows)
- Fire TV and host computer connected to the same trusted local network

### Python dependencies

| Package | Purpose |
|---|---|
| `PySide6>=6.7,<7` | Qt widgets and desktop GUI |

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Ubuntu / WSL system packages

```bash
sudo apt update
sudo apt install adb unzip python3-venv python3-pip -y
```

Verify ADB:

```bash
adb version
which adb
```

The usual Ubuntu executable path is `/usr/bin/adb`. If ADB is installed elsewhere, configure its full path under **Settings → ADB executable path**.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ZeroScopeIntelligence/FireTV-Manager.git
cd FireTV-Manager
```

### 2. Create and activate a virtual environment

Linux / WSL:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Python dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Start the application

```bash
python -m app
```

On Windows, ensure ADB Platform-Tools is installed and available in PATH, or configure its full executable path in the application.

## Prepare your Fire TV

Menu labels vary by Fire TV model and Fire OS release.

1. Connect the Fire TV Stick and computer to the same trusted home network.
2. Open **Settings → My Fire TV** (on some models this is **Device & Software**).
3. Open **About** and select the device name / Fire TV entry seven times if Developer Options are hidden.
4. Return to the previous menu and open **Developer Options**.
5. Enable **ADB Debugging**.
6. Find the Fire TV's IP address under **About → Network** or network settings.
7. Keep the Fire TV awake and accept the ADB debugging authorization prompt on the television when it appears.

Amazon's guide: [Connecting to Fire TV through ADB](https://developer.amazon.com/docs/fire-tv/connecting-adb-to-device).

## Using the application

### Devices tab

1. Enter your local IPv4 subnet in CIDR notation, for example `192.168.1.0/24`.
2. Enter the ADB port (commonly `5555`, unless your Fire TV or network setup uses a different port).
3. Select **Discover devices** to probe that subnet and port.
4. Select the discovered IP and choose **Connect selected IP**.
5. Approve the debugging authorization prompt on the Fire TV if requested.
6. Choose **Refresh ADB devices** to refresh the connected-device list.

### Install APK tab

1. Select **Browse** and choose an `.apk` file.
2. Select the authorized Fire TV in **Target device**.
3. Keep **Reinstall/update if the app is already installed** enabled to use ADB's reinstall option, or disable it for a fresh installation.
4. Click **Install APK**.
5. Review the result in the dialog and Logs tab.

An APK must be compatible with the device's CPU architecture (ABI), Android / Fire OS version, SDK requirements, and required hardware features. For example, an APK containing only 64-bit `arm64-v8a` native libraries will not install on a Fire TV that reports only 32-bit `armeabi-v7a` support.

Useful device checks:

```bash
adb devices -l
adb -s DEVICE_SERIAL shell getprop ro.product.cpu.abilist
adb -s DEVICE_SERIAL shell getprop ro.product.cpu.abi
adb -s DEVICE_SERIAL shell getprop ro.build.version.sdk
```

Replace `DEVICE_SERIAL` with the serial shown by `adb devices`, such as `192.168.0.166:5555`.

### Installed Apps tab

1. Select a connected device.
2. Click **Load installed apps**.
3. The application displays third-party package names returned by Android's package manager.
4. Select a package and click **Uninstall selected app**.
5. Confirm the prompt to proceed.

The view uses `pm list packages -3`, so it is not a complete inventory of system apps. Uninstallation may fail for protected or non-removable packages.

### Logs tab

The Logs tab displays timestamped application operations and errors. Use **Clear logs** to clear the current on-screen log.

### Settings tab

Set the full path to `adb` if it is not found automatically. Use **Test ADB** to verify that the configured executable runs. The default port can also be changed here.

## Troubleshooting

### ADB was not found

On Ubuntu / WSL:

```bash
sudo apt update
sudo apt install adb -y
which adb
adb version
```

Then set the returned path (commonly `/usr/bin/adb`) in Settings.

### No devices found

- Confirm ADB Debugging is enabled on the Fire TV.
- Confirm the TV and computer are on the same LAN / subnet.
- Check the Fire TV IP address and selected port.
- Check whether guest-network or client isolation is blocking local device traffic.
- Keep the Fire TV awake and watch for an authorization prompt.
- Try connecting from the terminal:

```bash
adb connect FIRE_TV_IP:5555
adb devices -l
```

Replace the IP and port with your device's values.

### ADB shows unauthorized

Look at the TV screen and accept the ADB debugging authorization prompt, then refresh the device list.

### INSTALL_FAILED_NO_MATCHING_ABIS

The APK's native libraries do not match the ABIs supported by the Fire TV. Check the device and package:

```bash
adb -s DEVICE_SERIAL shell getprop ro.product.cpu.abilist
unzip -l your-app.apk | grep 'lib/'
```

Choose an APK variant that includes a compatible ABI, such as `armeabi-v7a` for a device reporting that ABI. A universal APK may work if it contains the required native libraries. Renaming an APK does not convert its native code to another architecture.

If `unzip` is unavailable:

```bash
sudo apt install unzip
```

### GUI does not appear in WSL

This application uses PySide6. On Windows 11, WSLg normally provides GUI support. Check:

```bash
echo "$DISPLAY"
```

If no graphical display is available, use a supported Linux desktop session or run the application with Windows Python and Windows ADB.

## Security and responsible use

- Use this tool only with Fire TV devices you own or are authorized to administer.
- ADB debugging grants powerful control over the device. Disable ADB Debugging when you no longer need it.
- Only install APKs from sources you trust.
- Keep device debugging restricted to a trusted local network. Do not expose ADB to the public internet.
- This application does not bypass account controls, DRM, paid-app licensing, device restrictions, or application security.
- Network discovery is limited to the IPv4 subnet and TCP port explicitly entered by the user.

## Current limitations

- Discovery checks TCP reachability. It does not prove that every responding host is a Fire TV; connecting through ADB is the next validation step.
- Default discovery uses port `5555`; connection workflows and ports may differ by Fire OS version and device configuration.
- Installed-app listing is limited to third-party package names.
- An automated APK compatibility analyzer (ABI, SDK and feature checks) is planned; current installation errors are reported from ADB.
- The application has not been tested against every Fire TV model or Fire OS version.

## Roadmap

- APK compatibility analyzer (device ABI, APK ABI, SDK and feature checks).
- More detailed device information and package metadata.
- Improved connection workflow for Fire OS versions using dynamic ADB pairing.
- Exportable diagnostic logs.
- Windows executable packaging.

## License

Copyright (c) ZeroScope Solutions. All rights reserved.

Unless a separate license file or written permission states otherwise, no permission is granted to redistribute, modify, or use this project outside applicable copyright exceptions.
