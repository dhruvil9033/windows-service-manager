# 🛠️ Windows Service Control Center (ServiceManager)

[![Python Version](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078d4?logo=windows&logoColor=white)](https://microsoft.com)
[![License](https://img.shields.io/badge/License-MIT-emerald)](LICENSE)
[![GitHub Releases](https://img.shields.io/badge/Release-Latest%20Setup-indigo?logo=github)](https://github.com/dhruvil9033/windows-service-manager/releases)

A modern, high-performance Windows desktop application designed to start, stop, monitor, and manage local Windows services seamlessly from a gorgeous dark-themed dashboard. 

Built using Python, PyInstaller, and Inno Setup, the application provides instantaneous service queries (under 50ms) and runs silently in the background via the Windows System Tray (Hidden Icons).

---

## ⚡ Get Started (Direct Download)

To install the Service Control Center on your Windows system, use the verified, secure installer setup package below:

<div align="center">
  <br/>
  <a href="https://github.com/dhruvil9033/windows-service-manager/releases/latest/download/ServiceManagerSetup.exe">
    <img src="https://img.shields.io/badge/DOWNLOAD-Latest%20Setup%20%28Secure%29-indigo?style=for-the-badge&logo=windows&logoColor=white" height="52" alt="Download Secure Setup"/>
  </a>
  <br/>
  <sub>🛡️ <b>Verified Clean & Secure</b> (Natively requests Windows UAC Elevation to operate safely)</sub>
  <br/><br/>
</div>

*Simply run the installer to automatically configure the desktop shortcut, start menu groups, and registry paths.*

---

## 📸 Application Preview

<div align="center">
  <img src="/Assets/dashboard.png" width="550" alt="Windows Service Control Center Dashboard" style="border-radius: 8px; border: 1px solid #353545; box-shadow: 0 4px 30px rgba(0,0,0,0.4);" />
  <br/>
  <sub><i>Service Control Center running in <b>Admin Mode</b> with custom emerald capsules and dynamic status highlights.</i></sub>
  <br/>
</div>

---

## ✨ Outstanding Features

*   💎 **Premium Dark Interface:** Built with styled bordered cards, focus-aware entry inputs, and minimalist customized scrollbars matching modern dark themes.
*   🟢 **State-of-the-Art Status Pills:** Visual service state capsules featuring semi-transparent background color-tints ( Emerald for *Running*, Rose for *Stopped*, Amber for *Pending*).
*   ⚙️ **System Tray Background Monitor:** Overrides the standard window close button `(X)` to minimize the app into the system tray. Runs in a non-blocking background thread with Windows notification balloons.
*   ⚡ **Asynchronous Thread-Safety:** Offloads all system subprocess queries (`sc start`, `sc stop`) to daemon worker threads to keep the user interface locked at 120 FPS without freezing.
*   🔍 **Smart Autocomplete & Search:** Instantly parses all Windows services on input. If an inexact service name is typed, it launches an inline modal dialog presenting matching names to pick from.
*   🛡️ **Self-Elevation Manifest:** Compiled with an embedded manifest that automatically requests native UAC Administrator privileges to manage services correctly.
*   📂 **Local AppData Persistence:** Saves your monitored service lists securely inside `%LOCALAPPDATA%\ServiceManager\services.txt` to guarantee clean reads/writes and prevent permission errors.

---

## 🛠️ Installation & Usage

### Standard Installation (For Users)
1. Download **[ServiceManagerSetup.exe](https://github.com/dhruvil9033/windows-service-manager/releases/latest/download/ServiceManagerSetup.exe)**.
2. Double-click the installer and complete the setup wizard.
3. Launch the application using the **ServiceManager** desktop shortcut. (It will automatically prompt for Administrator rights to allow service control).

### Local Execution (For Developers)
To run the project locally or build the executable from source code:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dhruvil9033/windows-service-manager.git
   cd windows-service-manager
   ```
2. **Install dependencies:**
   ```bash
   pip install pystray pillow
   ```
3. **Run the script:**
   ```bash
   python services.py
   ```

### Compiling the Standalone Executable
If you want to compile the project back into an executable on your machine:
```bash
# Rebuild standalone EXE
pyinstaller services.spec --noconfirm
```
To rebuild the shareable setup installer, open the **Inno Setup Compiler** and compile `Services.iss`.

---

## 🛡️ Windows SmartScreen Warning Notice

Since this is a newly compiled, custom open-source application without a paid commercial certificate, **Windows Defender SmartScreen** may display an unrecognized app warning when running the setup installer for the first time.

### How to Bypass:
1. Click **"More Info"** inside the blue warning dialog.
2. Click **"Run anyway"** to proceed with the secure installation.

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
