import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import serial
import threading
import re
import time

class MarauderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Marauder Pro Controller")
        self.root.geometry("850x700")
        
        self.serial_port = None
        self.reading = False
        self.line_buffer = ""
        self.ap_vars = {}
        self.ap_labels = {}
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Connection Frame
        conn_frame = tk.Frame(root)
        conn_frame.pack(pady=5, fill=tk.X, padx=10)
        
        tk.Label(conn_frame, text="COM Port:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.port_entry = tk.Entry(conn_frame, width=15)
        self.port_entry.pack(side=tk.LEFT, padx=5)
        self.port_entry.insert(0, "COM4")
        
        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.toggle_connection, bg="lightgreen")
        self.connect_btn.pack(side=tk.LEFT, padx=5)
        
        # Tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Tab 1: Access Points & Deauth
        self.tab_ap = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ap, text="🎯 Деаутентификация & AP")
        
        ctrl_frame = tk.Frame(self.tab_ap)
        ctrl_frame.pack(fill=tk.X, pady=5)
        tk.Button(ctrl_frame, text="1. Сканировать AP (10с)", bg="lightblue", command=lambda: self.send_command("scanap")).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="2. Стоп скан", bg="yellow", command=lambda: self.send_command("stopscan")).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="3. Показать AP (Создаст галочки 👇)", bg="lightgreen", command=self.refresh_ap_list).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="Очистить UI список", command=self.clear_ap_list).pack(side=tk.RIGHT, padx=5)
        
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
        tk.Button(atk_frame, text="Выбрать все", command=self.select_all_aps).pack(side=tk.LEFT, padx=5)
        tk.Button(atk_frame, text="Снять все", command=self.select_no_aps).pack(side=tk.LEFT, padx=5)
        tk.Button(atk_frame, text="4. ATTACK SELECTED (Deauth)", bg="lightcoral", font=("Arial", 10, "bold"), command=self.attack_selected_deauth).pack(side=tk.LEFT, padx=15)
        tk.Button(atk_frame, text="5. STOP ATTACK", bg="orange", font=("Arial", 10, "bold"), command=lambda: self.send_command("stopattack")).pack(side=tk.LEFT, padx=5)

        # Tab 2: Sniffing
        self.tab_sniff = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sniff, text="📡 Сниффинг (Перехват)")
        self.setup_grid_buttons(self.tab_sniff, [
            ("Sniff Raw", "sniffraw"), ("Sniff Beacon", "sniffbeacon"),
            ("Sniff Probe", "sniffprobe"), ("Sniff PMKID", "sniffpmkid"),
            ("Sniff Pwn", "sniffpwn"), ("Sniff ESP", "sniffesp"),
            ("Sniff Deauth", "sniffdeauth"), ("Остановить (Stop)", "stopscan")
        ])
        
        # Tab 3: Spam & Troll
        self.tab_spam = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_spam, text="😈 Спам сетями (Beacon Spam)")
        
        custom_ssid_frame = tk.Frame(self.tab_spam)
        custom_ssid_frame.pack(fill=tk.X, pady=10, padx=10)
        tk.Label(custom_ssid_frame, text="Свое название:").pack(side=tk.LEFT)
        self.custom_ssid_name = tk.Entry(custom_ssid_frame, width=20)
        self.custom_ssid_name.pack(side=tk.LEFT, padx=5)
        self.custom_ssid_name.insert(0, "Free WiFi")
        tk.Label(custom_ssid_frame, text="Кол-во:").pack(side=tk.LEFT)
        self.custom_ssid_qty = tk.Entry(custom_ssid_frame, width=5)
        self.custom_ssid_qty.pack(side=tk.LEFT, padx=5)
        self.custom_ssid_qty.insert(0, "5")
        tk.Button(custom_ssid_frame, text="Сгенерировать", bg="lightgreen", command=self.add_custom_ssids).pack(side=tk.LEFT, padx=10)

        grid_spam = tk.Frame(self.tab_spam)
        grid_spam.pack(fill=tk.BOTH, expand=True)
        self.setup_grid_buttons(grid_spam, [
            ("20 СЛУЧАЙНЫХ сетей", "ssid -a -g 20"), ("Показать список", "list -s"),
            ("▶ ЗАПУСТИТЬ SPAM", "start_beacon_spam"), ("Rickroll Attack", "attack -t rickroll"),
            ("Karma Attack", "karma"), ("Очистить список (важно)", "clearlist -s"),
            ("⏹ ОСТАНОВИТЬ АТАКУ", "stopattack")
        ])
        
        # Tab 4: System Options
        self.tab_sys = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sys, text="🛠️ Системные и Разное")
        self.setup_grid_buttons(self.tab_sys, [
            ("Packet Monitor", "packetcount"), ("Sys Info", "info"),
            ("Очистить память AP (clearlist)", "clearlist -a"), ("Reboot Board", "reboot"),
            ("GPS Data", "gpsdata"), ("LED Rainbow", "led -p rainbow"),
            ("PingScan", "pingscan"), ("ArpScan", "arpscan")
        ])
        
        # Custom Command Input
        cmd_frame = tk.Frame(root)
        cmd_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(cmd_frame, text="Ручная команда:").pack(side=tk.LEFT)
        self.cmd_entry = tk.Entry(cmd_frame, width=50)
        self.cmd_entry.pack(side=tk.LEFT, padx=5)
        self.cmd_entry.bind('<Return>', lambda event: self.send_custom())
        tk.Button(cmd_frame, text="Отправить", bg="lightblue", command=self.send_custom).pack(side=tk.LEFT)
        tk.Button(cmd_frame, text="Очистить терминал", command=lambda: self.log.delete('1.0', tk.END)).pack(side=tk.RIGHT)
        
        # Terminal Output
        self.log = scrolledtext.ScrolledText(root, bg="#1e1e1e", fg="#00ff00", font=("Consolas", 10), height=14)
        self.log.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

    def setup_grid_buttons(self, parent, btns):
        col, row = 0, 0
        for name, cmd in btns:
            if cmd == "start_beacon_spam":
                tk.Button(parent, text=name, width=25, height=2, command=self.start_beacon_spam).grid(row=row, column=col, padx=10, pady=10)
            else:
                tk.Button(parent, text=name, width=25, height=2, command=lambda c=cmd: self.send_command(c)).grid(row=row, column=col, padx=10, pady=10)
            col += 1
            if col > 2:
                col = 0
                row += 1

    def start_beacon_spam(self):
        # Нужно сначала "выбрать" сгенерированные сети, чтобы плата знала, чем спамить
        self.send_command("select -s all")
        self.root.after(500, lambda: self.send_command("attack -t beacon -l"))

    def toggle_connection(self):
        if self.serial_port and self.serial_port.is_open:
            self.reading = False
            self.serial_port.close()
            self.connect_btn.config(text="Connect", bg="lightgreen")
            self.log_msg("Отключено.\n")
        else:
            port = self.port_entry.get().strip()
            try:
                self.serial_port = serial.Serial(port, 115200, timeout=1)
                self.reading = True
                self.connect_btn.config(text="Disconnect", bg="lightcoral")
                self.log_msg(f"Успешно подключено к {port} (Baud: 115200).\n")
                threading.Thread(target=self.read_from_port, daemon=True).start()
                self.send_command("")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось подключиться: {e}\n\nВозможно, у вас открыта старая версия программы или PuTTY! Закройте их.")

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
            messagebox.showwarning("Внимание", "Ты не выбрал ни одной сети для атаки (нет галочек)!")
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
            messagebox.showwarning("Ошибка", "Количество должно быть числом!")
            return
            
        if not name or qty < 1:
            return
            
        def runner():
            self.log_msg(f"\n[INFO] Генерирую {qty} сетей: '{name}'...\n")
            for i in range(1, qty + 1):
                suffix = f" {i}" if qty > 1 else ""
                self.send_command(f'ssid -a -n "{name}{suffix}"')
                time.sleep(0.3)
            self.log_msg(f"[INFO] Успешно сгенерировано!\n")
                
        threading.Thread(target=runner, daemon=True).start()

    def send_command(self, cmd):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.write((cmd + "\n").encode('utf-8'))
            self.log.insert(tk.END, f"\n[ОТПРАВЛЕНО]: {cmd}\n")
            self.log.see(tk.END)
        else:
            self.log_msg("Ошибка: Плата не подключена!\n")

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
