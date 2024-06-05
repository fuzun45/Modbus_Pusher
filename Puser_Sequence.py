import tkinter as tk
from tkinter import simpledialog, messagebox
from pymodbus.client.sync import ModbusTcpClient
import threading
import time
import itertools

class CustomDialog(simpledialog.Dialog):
    def __init__(self, parent, title=None):
        self.ip_address = ""
        self.port = ""
        self.coil_numbers = ""
        super().__init__(parent, title)

    def body(self, master):
        tk.Label(master, text="IP Address:").grid(row=0)
        tk.Label(master, text="Port:").grid(row=1)
        tk.Label(master, text="Coil Numbers (comma separated):").grid(row=2)
        
        self.ip_entry = tk.Entry(master)
        self.port_entry = tk.Entry(master)
        self.coils_entry = tk.Entry(master)

        self.ip_entry.insert(0, "10.3.200.10")
        self.port_entry.insert(0, "502")
        self.coils_entry.insert(0, "8192,8193,8194,8195")

        self.ip_entry.bind("<FocusIn>", self.clear_ip_placeholder)
        self.port_entry.bind("<FocusIn>", self.clear_port_placeholder)
        self.coils_entry.bind("<FocusIn>", self.clear_coils_placeholder)

        self.ip_entry.grid(row=0, column=1)
        self.port_entry.grid(row=1, column=1)
        self.coils_entry.grid(row=2, column=1)

        return self.ip_entry

    def clear_ip_placeholder(self, event):
        if self.ip_entry.get() == "Enter IP address":
            self.ip_entry.delete(0, tk.END)

    def clear_port_placeholder(self, event):
        if self.port_entry.get() == "Enter port number":
            self.port_entry.delete(0, tk.END)

    def clear_coils_placeholder(self, event):
        if self.coils_entry.get() == "8192,8193,8194,8195":
            self.coils_entry.delete(0, tk.END)


    def apply(self):
        self.ip_address = self.ip_entry.get()
        self.port = int(self.port_entry.get())
        self.coil_numbers = list(map(int, self.coils_entry.get().split(',')))

class ModbusApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modbus Coil Control")
        
        dialog = CustomDialog(self.root, title="Modbus Settings")
        self.ip_address = dialog.ip_address
        self.port = dialog.port
        self.coil_numbers = dialog.coil_numbers
        
        self.modbus_client = ModbusTcpClient(self.ip_address, self.port)
        if not self.modbus_client.connect():
            messagebox.showerror("Connection Error", "Failed to connect to Modbus server")
            self.root.destroy()
            return
        
        self.buttons = []
        self.create_widgets()
        self.create_buttons()

    def create_widgets(self):
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=30)

        self.duration_frame = tk.Frame(self.root)
        self.duration_frame.pack(pady=10)

        self.duration_label = tk.Label(self.duration_frame, text="Duration (seconds):")
        self.duration_label.pack(side=tk.LEFT, padx=10)
        
        self.duration_entry = tk.Entry(self.duration_frame)
        self.duration_entry.insert(0, "60")
        self.duration_entry.pack(side=tk.LEFT, padx=10)

        self.automatic_button = tk.Button(self.root, text="Automatic Control Settings", command=self.open_automatic_control)
        self.automatic_button.pack(pady=10)

    def create_buttons(self):
        self.canvas = tk.Canvas(self.button_frame, width=350, height=350)
        self.canvas.pack(pady=20)

        button_size = 80
        padding = 60
        for i, coil in enumerate(self.coil_numbers):
            x = padding + (i % 2) * (button_size + padding)
            y = padding + (i // 2) * (button_size + padding)
            btn = self.canvas.create_oval(x, y, x+button_size, y+button_size, fill="#F70D1A", outline="black")
            self.canvas.create_text(x + button_size / 2, y - 20, text=f"Button {i+1}", font=("Arial", 12))
            self.canvas.create_text(x + button_size / 2, y + button_size + 20, text=f"Coil {coil}", font=("Arial", 12))
            self.buttons.append((btn, coil, self.canvas))
            self.canvas.tag_bind(btn, "<Button-1>", lambda event, c=coil, b=btn: self.toggle_coil(c, b))

        self.update_button_colors()

    def toggle_coil(self, coil, btn):
        try:
            duration = float(self.duration_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid duration in seconds.")
            return
        
        thread = threading.Thread(target=self.toggle_coil_thread, args=(coil, btn, duration))
        thread.start()

    def toggle_coil_thread(self, coil, btn, duration):
        try:
            current_state = self.modbus_client.read_coils(coil, 1).bits[0]
            self.modbus_client.write_coil(coil, not current_state)
            self.update_button_color(btn, not current_state)
            time.sleep(duration)
            self.modbus_client.write_coil(coil, current_state)
            self.update_button_color(btn, current_state)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_button_colors(self):
        for btn, coil, canvas in self.buttons:
            try:
                current_state = self.modbus_client.read_coils(coil, 1).bits[0]
                self.update_button_color(btn, current_state)
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def update_button_color(self, btn, state):
        color = "#039b4e" if state else "#F70D1A"
        for canvas, item in [(canvas, item) for item, coil, canvas in self.buttons if item == btn]:
            canvas.itemconfig(item, fill=color)

    def open_automatic_control(self):
        self.auto_control_window = tk.Toplevel(self.root)
        self.auto_control_window.title("Automatic Control Settings")
        
        tk.Label(self.auto_control_window, text="Button Sequence:").grid(row=0, column=0, pady=10, padx=10)
        self.sequence_entry = tk.Entry(self.auto_control_window)
        self.sequence_entry.insert(0, "1,2,3,4")
        self.sequence_entry.grid(row=0, column=1, pady=10, padx=10)

        tk.Label(self.auto_control_window, text="Press Duration (seconds):").grid(row=1, column=0, pady=10, padx=10)
        self.press_duration_entry = tk.Entry(self.auto_control_window)
        self.press_duration_entry.insert(0, "2")
        self.press_duration_entry.grid(row=1, column=1, pady=10, padx=10)
        
        tk.Label(self.auto_control_window, text="Wait Duration (seconds):").grid(row=2, column=0, pady=10, padx=10)
        self.wait_duration_entry = tk.Entry(self.auto_control_window)
        self.wait_duration_entry.insert(0, "1")
        self.wait_duration_entry.grid(row=2, column=1, pady=10, padx=10)

        self.start_auto_button = tk.Button(self.auto_control_window, text="Start", command=self.start_automatic_control)
        self.start_auto_button.grid(row=3, column=0, pady=10, padx=10)

        self.stop_auto_button = tk.Button(self.auto_control_window, text="Stop", command=self.stop_automatic_control)
        self.stop_auto_button.grid(row=3, column=1, pady=10, padx=10)

    def start_automatic_control(self):
        try:
            sequence = list(map(int, self.sequence_entry.get().split(',')))
            press_duration = float(self.press_duration_entry.get())
            wait_duration = float(self.wait_duration_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid durations and sequence.")
            return

        self.auto_control_running = True
        thread = threading.Thread(target=self.auto_control_thread, args=(sequence, press_duration, wait_duration))
        thread.start()

    def auto_control_thread(self, sequence, press_duration, wait_duration):
        try:
            while self.auto_control_running:
                for button in sequence:
                    if not self.auto_control_running:
                        return
                    coil = self.coil_numbers[button - 1]
                    self.toggle_coil_thread(coil, self.buttons[button - 1][0], press_duration)
                    time.sleep(wait_duration)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def stop_automatic_control(self):
        self.auto_control_running = False
        for _, coil, _ in self.buttons:
            self.modbus_client.write_coil(coil, False)
            self.update_button_colors()

    def on_closing(self):
        self.modbus_client.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
