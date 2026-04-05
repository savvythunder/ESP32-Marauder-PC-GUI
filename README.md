# 📡 ESP32 Marauder Pro Controller (PC GUI)

A lightweight, feature-rich Graphical User Interface (GUI) written in Python (Tkinter) for controlling the **ESP32 Marauder** firmware. Designed with support for newer architectures (like the **ESP32-C5**) and optimized for quick Wi-Fi auditing, Deauth attacks, and Beacon Spamming directly from your Desktop.

## 🚀 Features
- **One-Click Connecting**: Automatically connects to your ESP32's COM port.
- **Smart AP Parsing**: Extracts Networks / Access Points directly from the terminal using relaxed regex logic and turns them into selectable checkboxes.
- **Batched Deauthentication**: Select multiple APs visually and launch Deauth attacks instantly.
- **Custom Beacon Spammer**: Generate specific quantities of custom SSIDs (e.g. `Free WiFi 1`, `Free WiFi 2`) and deploy beacon spam attacks.
- **Built-in Console**: Real-time read/write Serial terminal so you can see exact commands and board responses.
- **Categorized Tabs**: All Marauder commands logically grouped under `Access Points`, `Sniffing`, `Spam & Troll`, and `System Options`.

## 🛠 Prerequisites
- Python 3.x
- `pyserial` module
- Any ESP32 hardware flashed with the [ESP32Marauder](https://github.com/justcallmekoko/ESP32Marauder) firmware.

## 📥 Installation & Usage
1. Clone this repository:
   ```bash
   git clone https://github.com/wubery/ESP32-Marauder-PC-GUI.git
   ```
2. Install the required dependencies:
   ```bash
   pip install pyserial
   ```
3. Run the GUI:
   - Double-click `Start_Marauder.bat` (Windows)
   - Or run `python marauder_gui.py` from your terminal.

## ⚠️ Disclaimer
This tool is intended strictly for educational purposes, security auditing on networks you have legal authorization to test, and hardware development. Do **NOT** use this software to attack arbitrary networks. You are solely responsible for how you use this software.
