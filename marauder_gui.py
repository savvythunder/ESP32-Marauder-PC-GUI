import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import re
import time
import json
import os
import sys

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class MarauderGUI:
    def __init__(self, root):
        self.root = root
        
        self.load_translations()
        self.lang = "en"
        self.t = self.translations.get(self.lang, {})

        self.serial_port = None
        self.reading = False
        self.line_buffer = ""
        self.ap_vars = {}
        self.ap_labels = {}
        
        self.setup_ui()

    def load_translations(self):
        try:
            trans_path = os.path.join(get_script_dir(), "translations.json")
            with open(trans_path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception as e:
            print(f"Error loading translations: {e}")
            self.translations = {"en": {}, "ru": {}}
            
    def set_language(self, lang):
        self.lang = lang
        self.t = self.translations.get(lang, self.translations.get("en", {}))
        self.update_texts()

    def setup_ui(self):
        self.root.title(self.t.get("title", "ESP32 Marauder Pro Controller"))
        self.root.geometry("850x700")
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Language Selection
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        self.lbl_lang = tk.Label(top_frame, text=self.t.get("language", "Language:"))
        self.lbl_lang.pack(side=tk.RIGHT)
        
        self.lang_var = tk.StringVar(value=self.lang)
        self.lang_combo = ttk.Combobox(top_frame, textvariable=self.lang_var, values=["en", "ru"], state="readonly", width=5)
        self.lang_combo.pack(side=tk.RIGHT, padx=5)
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self.set_language(self.lang_var.get()))
        
        # Connection Frame
        conn_frame = tk.Frame(self.root)
        conn_frame.pack(pady=5, fill=tk.X, padx=10)
        
        self.lbl_com = tk.Label(conn_frame, text=self.t.get("com_port", "COM Port:"), font=("Arial", 10, "bold"))
        self.lbl_com.pack(side=tk.LEFT)
        self.port_entry = tk.Entry(conn_frame, width=15)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        self.port_entry.insert(0, "COM4")
        
        self.connect_btn = tk.Button(conn_frame, text=self.t.get("connect", "Connect"), command=self.toggle_connection, bg="lightgreen")
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: Access Points & Deauth
        self.tab_ap = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ap, text=self.t.get("tab_ap", "🎯 Deauth & AP"))
        
        ctrl_frame = tk.Frame(self.tab_ap)
        ctrl_frame.pack(fill=tk.X, pady=5)
        self.btn_scan_ap = tk.Button(ctrl_frame, text=self.t.get("scan_ap", "1. Scan AP (10s)"), bg="lightblue", command=lambda: self.send_command("scanap"))
        self.btn_scan_ap.pack(side=tk.LEFT, padx=5)
        self.btn_stop_scan = tk.Button(ctrl_frame, text=self.t.get("stop_scan", "2. Stop Scan"), bg="yellow", command=lambda: self.send_command("stopscan"))
        self.btn_stop_scan.pack(side=tk.LEFT, padx=5)
        self.btn_show_ap = tk.Button(ctrl_frame, text=self.t.get("show_ap", "3. Show AP"), bg="lightgreen", command=self.refresh_ap_list)
        self.btn_show_ap.pack(side=tk.LEFT, padx=5)
        self.btn_clear_ui = tk.Button(ctrl_frame, text=self.t.get("clear_ui_list", "Clear UI list"), command=self.clear_ap_list)
        self.btn_clear_ui.pack(side=tk.RIGHT, padx=5)
        
        # Checkboxes area
        scroll_frame = tk.Frame(self.tab_ap, bd=2, relief="sunken")
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.ap_canvas = tk.Canvas(scroll_frame, bg="white")
        self.ap_scrollbar = ttk.Scrollbar(scroll_frame, orient="vertical", command=self.ap_canvas.yview)
        self.ap_frame = tk.Frame(self.ap_canvas, bg="white")
        
        self.ap_frame.bind("<Configure>", lambda e: self.ap_canvas.configure(scrollregion=self.ap_canvas.bbox("all")))
        self.ap_canvas.create_window((0, 0), window=self.ap_frame, anchor="nw")
        self.ap_canvas.configure(yscrollcommand=self.ap_scrollbar.set)
        
        self.ap_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ap_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        atk_frame = tk.Frame(self.tab_ap)
        atk_frame.pack(fill=tk.X, pady=5)
        self.btn_select_all = tk.Button(atk_frame, text=self.t.get("select_all", "Select all"), command=self.select_all_aps)
        self.btn_select_all.pack(side=tk.LEFT, padx=5)
        self.btn_select_none = tk.Button(atk_frame, text=self.t.get("select_none", "Deselect all"), command=self.select_no_aps)
        self.btn_select_none.pack(side=tk.LEFT, padx=5)
        self.btn_atk_sel = tk.Button(atk_frame, text=self.t.get("attack_selected", "4. ATTACK SELECTED"), bg="lightcoral", font=("Arial", 10, "bold"), command=self.attack_selected_deauth)
        self.btn_atk_sel.pack(side=tk.LEFT, padx=15)
        self.btn_stop_atk = tk.Button(atk_frame, text=self.t.get("stop_attack", "5. STOP ATTACK"), bg="orange", font=("Arial", 10, "bold"), command=lambda: self.send_command("stopattack"))
        self.btn_stop_atk.pack(side=tk.LEFT, padx=5)

        # Tab 2: Sniffing
        self.tab_sniff = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sniff, text=self.t.get("tab_sniff", "📡 Sniffing (Capture)"))
        self.sniff_buttons = []
        self.setup_grid_buttons(self.tab_sniff, [
            ("sniff_raw", "sniffraw"), ("sniff_beacon", "sniffbeacon"),
            ("sniff_probe", "sniffprobe"), ("sniff_pmkid", "sniffpmkid"),
            ("sniff_pwn", "sniffpwn"), ("sniff_esp", "sniffesp"),
            ("sniff_deauth", "sniffdeauth"), ("stop_sniff", "stopscan")
        ], self.sniff_buttons)
        
        # Tab 3: Spam & Troll
        self.tab_spam = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_spam, text=self.t.get("tab_spam", "😈 Beacon Spam"))
        
        custom_ssid_frame = tk.Frame(self.tab_spam)
        custom_ssid_frame.pack(fill=tk.X, pady=10, padx=10)
        self.lbl_custom_ssid = tk.Label(custom_ssid_frame, text=self.t.get("custom_ssid", "Custom Name:"))
        self.lbl_custom_ssid.pack(side=tk.LEFT)
        self.custom_ssid_name = tk.Entry(custom_ssid_frame, width=20)
        self.custom_ssid_name.pack(side=tk.LEFT, padx=5)
        self.custom_ssid_name.insert(0, "Free WiFi")
        self.lbl_qty = tk.Label(custom_ssid_frame, text=self.t.get("qty", "Qty:"))
        self.lbl_qty.pack(side=tk.LEFT)
        self.custom_ssid_qty = tk.Entry(custom_ssid_frame, width=5)
        self.custom_ssid_qty.pack(side=tk.LEFT, padx=5)
        self.custom_ssid_qty.insert(0, "5")
        self.btn_gen = tk.Button(custom_ssid_frame, text=self.t.get("generate", "Generate"), bg="lightgreen", command=self.add_custom_ssids)
        self.btn_gen.pack(side=tk.LEFT, padx=10)

        grid_spam = tk.Frame(self.tab_spam)
        grid_spam.pack(fill=tk.BOTH, expand=True)
        self.spam_buttons = []
        self.setup_grid_buttons(grid_spam, [
            ("spam_20_random", "ssid -a -g 20"), ("show_list", "list -s"),
            ("start_spam", "start_beacon_spam"), ("rickroll", "attack -t rickroll"),
            ("karma", "karma"), ("clear_list", "clearlist -s"),
            ("stop_spam", "stopattack")
        ], self.spam_buttons)
        
        # Tab 4: System Options
        self.tab_sys = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sys, text=self.t.get("tab_sys", "🛠️ System & Misc"))
        self.sys_buttons = []
        self.setup_grid_buttons(self.tab_sys, [
            ("packet_monitor", "packetcount"), ("sys_info", "info"),
            ("clear_ap_memory", "clearlist -a"), ("reboot_board", "reboot"),
            ("gps_data", "gpsdata"), ("led_rainbow", "led -p rainbow"),
            ("ping_scan", "pingscan"), ("arp_scan", "arpscan")
        ], self.sys_buttons)
        
        # Custom Command Input
        cmd_frame = tk.Frame(self.root)
        cmd_frame.pack(fill=tk.X, padx=10, pady=5)
        self.lbl_man_cmd = tk.Label(cmd_frame, text=self.t.get("manual_cmd", "Manual Command:"))
        self.lbl_man_cmd.pack(side=tk.LEFT)
        self.cmd_entry = tk.Entry(cmd_frame, width=50)
        self.cmd_entry.pack(side=tk.LEFT, padx=5)
        self.cmd_entry.bind('<Return>', lambda event: self.send_custom())
        self.btn_send = tk.Button(cmd_frame, text=self.t.get("send", "Send"), bg="lightblue", command=self.send_custom)
        self.btn_send.pack(side=tk.LEFT)
        self.btn_clear_term = tk.Button(cmd_frame, text=self.t.get("clear_term", "Clear Terminal"), command=lambda: self.log.delete('1.0', tk.END))
        self.btn_clear_term.pack(side=tk.RIGHT)
        
        # Terminal Output
        self.log = scrolledtext.ScrolledText(self.root, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10), height=14)
        self.log.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

    def setup_grid_buttons(self, parent, btns, btn_list):
        col, row = 0, 0
        for name_key, cmd in btns:
            text = self.t.get(name_key, name_key)
            if cmd == "start_beacon_spam":
                btn = tk.Button(parent, text=text, width=25, height=2, command=self.start_beacon_spam)
                btn.grid(row=row, column=col, padx=10, pady=10)
            else:
                btn = tk.Button(parent, text=text, width=25, height=2, command=lambda c=cmd: self.send_command(c))
                btn.grid(row=row, column=col, padx=10, pady=10)
            btn_list.append((btn, name_key))
            col += 1
            if col > 2:
                col = 0
                row += 1

    def update_texts(self):
        self.root.title(self.t.get("title", "ESP32 Marauder Pro Controller"))
        self.lbl_lang.config(text=self.t.get("language", "Language:"))
        self.lbl_com.config(text=self.t.get("com_port", "COM Port:"))
        if self.serial_port and self.serial_port.is_open:
            self.connect_btn.config(text=self.t.get("disconnect", "Disconnect"))
        else:
            self.connect_btn.config(text=self.t.get("connect", "Connect"))
            
        self.notebook.tab(self.tab_ap, text=self.t.get("tab_ap", "🎯 Deauth & AP"))
        self.btn_scan_ap.config(text=self.t.get("scan_ap", "1. Scan AP (10s)"))
        self.btn_stop_scan.config(text=self.t.get("stop_scan", "2. Stop Scan"))
        self.btn_show_ap.config(text=self.t.get("show_ap", "3. Show AP"))
        self.btn_clear_ui.config(text=self.t.get("clear_ui_list", "Clear UI list"))
        self.btn_select_all.config(text=self.t.get("select_all", "Select all"))
        self.btn_select_none.config(text=self.t.get("select_none", "Deselect all"))
        self.btn_atk_sel.config(text=self.t.get("attack_selected", "4. ATTACK SELECTED"))
        self.btn_stop_atk.config(text=self.t.get("stop_attack", "5. STOP ATTACK"))
        
        self.notebook.tab(self.tab_sniff, text=self.t.get("tab_sniff", "📡 Sniffing (Capture)"))
        for btn, key in self.sniff_buttons:
            btn.config(text=self.t.get(key, key))
            
        self.notebook.tab(self.tab_spam, text=self.t.get("tab_spam", "😈 Beacon Spam"))
        self.lbl_custom_ssid.config(text=self.t.get("custom_ssid", "Custom Name:"))
        self.lbl_qty.config(text=self.t.get("qty", "Qty:"))
        self.btn_gen.config(text=self.t.get("generate", "Generate"))
        for btn, key in self.spam_buttons:
            btn.config(text=self.t.get(key, key))
            
        self.notebook.tab(self.tab_sys, text=self.t.get("tab_sys", "🛠️ System & Misc"))
        for btn, key in self.sys_buttons:
            btn.config(text=self.t.get(key, key))
            
        self.lbl_man_cmd.config(text=self.t.get("manual_cmd", "Manual Command:"))
        self.btn_send.config(text=self.t.get("send", "Send"))
        self.btn_clear_term.config(text=self.t.get("clear_term", "Clear Terminal"))

    def start_beacon_spam(self):
        # Нужно сначала "выбрать" сгенерированные сети, чтобы плата знала, чем спамить
        self.send_command("select -s all")
        self.root.after(500, lambda: self.send_command("attack -t beacon -l"))

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.reading = False
            self.serial_port.close()
            self.connect_btn.config(text=self.t.get("connect", "Connect"), bg="lightgreen")
            self.log_msg(self.t.get("disconnected", "Disconnected.\n"))
        else:
            port = self.port_entry.get().strip()
            try:
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self.reading = True
                self.connect_btn.config(text=self.t.get("disconnect", "Disconnect"), bg="lightcoral")
                self.log_msg(self.t.get("connected_to", "Successfully connected to {port} (Baud: 115200).\n").format(port=port))
                threading.Thread(target=self.read_from_port, daemon=True).start()
                self.send_command("")
            except Exception as e:
                title = self.t.get("conn_error_title", "Error")
                msg = self.t.get("conn_error_msg", "Could not connect: {error}\n\nPerhaps you have an old version of the program or PuTTY open! Close them.").format(error=str(e))
                messagebox.showerror(title, msg)

    def read_from_port(self):
        while self.reading and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting).decode('utf-8', errors='ignore')
                    self.root.after(0, self.process_incoming_data, data)
            except Exception:
                break

    def process_incoming_data(self, data):
        self.log_msg(data)
        self.line_buffer += data
        if '\n' in self.line_buffer:
            lines = self.line_buffer.split('\n')
            self.line_buffer = lines.pop()
            
            # Регулярное выражение для удаления скрытых цветовых кодов (ANSI)
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            
            for line in lines:
                line = line.strip()
                clean_line = ansi_escape.sub('', line)
                
                # Максимально упрощенный поиск: строка начинается с [цифры]
                match = re.search(r'^\[\s*(\d+)\s*\]\s*(.+)', clean_line)
                if match:
                    ap_id = match.group(1)
                    if ap_id not in self.ap_vars:
                        var = tk.IntVar()
                        self.ap_vars[ap_id] = var
                        chk = tk.Checkbutton(self.ap_frame, text=clean_line, variable=var, bg="white", font=("Consolas", 10))
                        chk.pack(anchor="w", padx=5)
                        self.ap_labels[ap_id] = chk

    def clear_ap_list(self):
        for widget in self.ap_frame.winfo_children():
            widget.destroy()
        self.ap_vars.clear()
        self.ap_labels.clear()

    def refresh_ap_list(self):
        self.clear_ap_list()
        self.send_command("list -a")

    def select_all_aps(self):
        for var in self.ap_vars.values():
            var.set(1)

    def select_no_aps(self):
        for var in self.ap_vars.values():
            var.set(0)

    def attack_selected_deauth(self):
        selected_ids = [str(k) for k, v in self.ap_vars.items() if v.get() == 1]
        if not selected_ids:
            title = self.t.get("warning_title", "Warning")
            msg = self.t.get("no_ap_selected", "You have not selected any network to attack (no checkboxes)!")
            messagebox.showwarning(title, msg)
            return
        id_str = ",".join(selected_ids)
        self.send_command(f"select -a {id_str}")
        # Задержка полсекунды перед самой атакой
        self.root.after(500, lambda: self.send_command("attack -t deauth"))

    def add_custom_ssids(self):
        name = self.custom_ssid_name.get().strip()
        try:
            qty = int(self.custom_ssid_qty.get().strip())
        except ValueError:
            title = self.t.get("qty_error_title", "Error")
            msg = self.t.get("qty_error", "Quantity must be a number!")
            messagebox.showwarning(title, msg)
            return
            
        if not name or qty < 1:
            return
            
        def runner():
            msg = self.t.get("gen_networks", "\n[INFO] Generating {qty} networks: '{name}'...\n").format(qty=qty, name=name)
            self.log_msg(msg)
            for i in range(1, qty + 1):
                suffix = f" {i}" if qty > 1 else ""
                self.send_command(f'ssid -a -n "{name}{suffix}"')
                time.sleep(0.3)
            success_msg = self.t.get("gen_success", "[INFO] Successfully generated!\n")
            self.log_msg(success_msg)
                
        threading.Thread(target=runner, daemon=True).start()

    def send_command(self, cmd):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((cmd + "\n").encode('utf-8'))
            sent_msg = self.t.get("sent", "\n[SENT]: {cmd}\n").format(cmd=cmd)
            self.log.insert(tk.END, sent_msg)
            self.log.see(tk.END)
        else:
            not_connected_msg = self.t.get("not_connected", "Error: Board is not connected!\n")
            self.log_msg(not_connected_msg)

    def send_custom(self):
        cmd = self.cmd_entry.get().strip()
        if cmd:
            self.send_command(cmd)
            self.cmd_entry.delete(0, tk.END)

    def log_msg(self, msg):
        self.log.insert(tk.END, msg)
        self.log.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = MarauderGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (setattr(app, 'reading', False), root.destroy()))
    root.mainloop()
