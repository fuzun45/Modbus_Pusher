import tkinter as tk
from tkinter import simpledialog, messagebox, Menu, Toplevel, StringVar, OptionMenu, BooleanVar, Checkbutton, Frame, LEFT, Label, Entry, Button
from pymodbus.client.sync import ModbusTcpClient
import threading
import time

# Common dialog class for settings
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

# Main application class
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
        
        self.manual_control_running = False
        self.auto_control_running = False
        self.buttons = []
        self.create_widgets()
        self.create_buttons()
        self.create_menu()

    def create_menu(self):
        menubar = Menu(self.root)
        
        control_menu = Menu(menubar, tearoff=0)
        control_menu.add_command(label="Manual Control", command=self.manual_control)
        control_menu.add_command(label="Automatic Control", command=self.open_automatic_control)
        control_menu.add_separator()
        control_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="Control", menu=control_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def show_about(self):
        messagebox.showinfo("About", "Modbus Coil Control\nVersion 1.0\nDeveloped by OpenAI")

    def create_widgets(self):
        self.duration_frame = tk.Frame(self.root)
        self.duration_frame.pack(pady=10)

        self.duration_label = tk.Label(self.duration_frame, text="Duration (seconds):")
        self.duration_label.pack(side=tk.LEFT, padx=10)
        
        self.duration_entry = tk.Entry(self.duration_frame)
        self.duration_entry.insert(0, "60")
        self.duration_entry.pack(side=tk.LEFT, padx=10)

        self.stop_button = tk.Button(self.root, text="Stop", command=self.stop_all_control, state=tk.DISABLED)
        self.stop_button.pack(pady=10)

    def create_buttons(self):
        canvas = tk.Canvas(self.root, width=500, height=500)
        canvas.pack(pady=20)

        button_size = 80
        padding = 60
        for i, coil in enumerate(self.coil_numbers):
            x = padding + (i % 2) * (button_size + padding)
            y = padding + (i // 2) * (button_size + padding)
            btn = canvas.create_oval(x, y, x+button_size, y+button_size, fill="#F70D1A", outline="black")
            canvas.create_text(x + button_size/2, y + button_size/2 - 20, text=f"Button {i+1}", fill="black")
            canvas.create_text(x + button_size/2, y + button_size/2 + 20, text=f"Coil {coil}", fill="black")
            self.buttons.append((btn, coil, canvas))
            canvas.tag_bind(btn, "<Button-1>", lambda event, c=coil, b=btn: self.toggle_coil(c, b))

        self.update_button_colors()

    def toggle_coil(self, coil, btn):
        try:
            duration = float(self.duration_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter a valid duration in seconds.")
            return
        
        self.manual_control_running = True
        self.stop_button.config(state=tk.NORMAL)
        thread = threading.Thread(target=self.toggle_coil_thread, args=(coil, btn, duration))
        thread.start()

    def toggle_coil_thread(self, coil, btn, duration):
        try:
            current_state = self.modbus_client.read_coils(coil, 1).bits[0]
            self.modbus_client.write_coil(coil, not current_state)
            self.update_button_color(btn, not current_state)
            start_time = time.time()
            while time.time() - start_time < duration:
                if not self.manual_control_running:
                    self.modbus_client.write_coil(coil, current_state)
                    self.update_button_color(btn, current_state)
                    return
                time.sleep(0.1)
            self.modbus_client.write_coil(coil, current_state)
            self.update_button_color(btn, current_state)
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.stop_button.config(state=tk.DISABLED)
            self.manual_control_running = False

    def update_button_colors(self):
        for btn, coil, canvas in self.buttons:
            try:
                current_state = self.modbus_client.read_coils(coil, 1).bits[0]
                self.update_button_color(btn, current_state)
            except Exception as e:
                messagebox.showerror("Error", str(e))
    
    def update_button_color(self, btn, state):
        color = "green" if state else "#F70D1A"
        for canvas, item in [(canvas, item) for item, coil, canvas in self.buttons if item == btn]:
            canvas.itemconfig(item, fill=color)

    def manual_control(self):
        self.manual_control_running = False
        self.auto_control_running = False

    def open_automatic_control(self):
        self.auto_control_window = Toplevel(self.root)
        self.auto_control_window.title("Automatic Control Settings")

        Label(self.auto_control_window, text="Press Duration (seconds):").grid(row=0, column=0)
        self.press_duration_entry = Entry(self.auto_control_window)
        self.press_duration_entry.grid(row=0, column=1)

        Label(self.auto_control_window, text="Wait Duration (seconds):").grid(row=1, column=0)
        self.wait_duration_entry = Entry(self.auto_control_window)
        self.wait_duration_entry.grid(row=1, column=1)

        Label(self.auto_control_window, text="Select Button:").grid(row=2, column=0)
        self.button_var = StringVar(self.auto_control_window)
        self.button_var.set("Button 1")
        button_menu = OptionMenu(self.auto_control_window, self.button_var, *[f"Button {i+1}" for i in range(len(self.coil_numbers))])
        button_menu.grid(row=2, column=1)

        self.loop_var = BooleanVar()
        Checkbutton(self.auto_control_window, text="Loop", variable=self.loop_var).grid(row=3, columnspan=2)

        Button(self.auto_control_window, text="Start", command=self.start_automatic_control).grid(row=4, columnspan=2)
        self.stop_button = Button(self.auto_control_window, text="Stop", command=self.stop_automatic_control)
        self.stop_button.grid(row=5, columnspan=2)
    
    def start_automatic_control(self):
        try:
            press_duration = float(self.press_duration_entry.get())
            wait_duration = float(self.wait_duration_entry.get())
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid durations in seconds.")
            return
        
        button_index = int(self.button_var.get().split()[-1]) - 1
        coil = self.coil_numbers[button_index]
        self.auto_control_running = True
        self.stop_button.config(state=tk.NORMAL)

        def auto_control():
            while self.auto_control_running:
                self.toggle_coil_thread(coil, self.buttons[button_index][0], press_duration)
                time.sleep(wait_duration)
                if not self.loop_var.get():
                    break

        self.auto_control_thread = threading.Thread(target=auto_control)
        self.auto_control_thread.start()

    def stop_automatic_control(self):
        self.auto_control_running = False
        self.stop_button.config(state=tk.DISABLED)

    def stop_all_control(self):
        self.manual_control_running = False
        self.auto_control_running = False
        for btn, coil, canvas in self.buttons:
            self.modbus_client.write_coil(coil, False)
            self.update_button_color(btn, False)
        self.stop_button.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = ModbusApp(root)
    root.mainloop()
