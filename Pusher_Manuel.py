import tkinter as tk
from tkinter import Canvas, simpledialog, messagebox
from pymodbus.client.sync import ModbusTcpClient
import threading
import time

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
        self.create_buttons()
        self.create_widgets()

    def create_widgets(self):
        self.duration_frame = tk.Frame(self.root)
        self.duration_frame.pack(pady=20)

        self.duration_label = tk.Label(self.duration_frame, text="Duration (seconds):")
        self.duration_label.pack(side=tk.LEFT, padx=10)
        
        self.duration_entry = tk.Entry(self.duration_frame)
        self.duration_entry.insert(0, "10")
        self.duration_entry.pack(side=tk.LEFT, padx=10)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_manual_control, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

    def create_buttons(self):
        canvas = tk.Canvas(self.root, width=250, height=325)
        canvas.pack()

        button_size = 60
        padding = 40
        for i, coil in enumerate(self.coil_numbers):
            x = padding + (i % 2) * (button_size + padding)
            y = padding + (i // 2) * (button_size + padding)
            btn = canvas.create_oval(x, y, x+button_size, y+button_size, fill="#F70D1A", outline="black")
            canvas.create_text(x + button_size / 2, y - 10, text=f"Button {i+1}", font=("Arial", 10))
            canvas.create_text(x + button_size / 2, y + button_size + 10, text=f"Coil {coil}", font=("Arial", 10))
            self.buttons.append((btn, coil, canvas))
            canvas.tag_bind(btn, "<Button-1>", lambda event, c=coil, b=btn: self.toggle_coil(c, b))

        

        self.update_button_colors()

    def toggle_coil(self, coil, btn):
        try:
            duration = float(self.duration_entry.get())

            if duration<=0:
                duration=60
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid duration in seconds.")
            return
        
        self.stop_button.config(state=tk.NORMAL)
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

    def stop_manual_control(self):
        self.manual_control_running = False
        for _, coil, _ in self.buttons:
            try:
                self.modbus_client.write_coil(coil, False)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        self.update_button_colors()
        self.stop_button.config(state=tk.DISABLED)

    def on_closing(self):
        self.modbus_client.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
