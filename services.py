import sys
import os
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# --- Styles and Theme Constants ---
DARK_BG = "#1e1e24"
CARD_BG = "#2a2a35"
TEXT_COLOR = "#f5f5f7"
TEXT_MUTED = "#a0a0b0"
PRIMARY_COLOR = "#4c6ef5"      # Modern indigo/blue
PRIMARY_HOVER = "#3b5bdb"
ACCENT_GREEN = "#12b886"       # Green for Running
ACCENT_RED = "#fa5252"         # Red for Stopped
ACCENT_YELLOW = "#fcc419"      # Yellow for Unknown / Transition

def is_admin():
    """Check if the process is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Relaunch the script with Admin rights."""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

class ServiceChoiceDialog(tk.Toplevel):
    def __init__(self, parent, query, matches):
        super().__init__(parent)
        self.title("Select Service")
        self.geometry("520x420")
        self.configure(bg=DARK_BG)
        self.resizable(False, False)
        
        # Make modal
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.matches = matches # List of tuples: (name, display_name)
        
        # Header
        header_lbl = ttk.Label(
            self, 
            text=f"No exact match for '{query}'", 
            font=("Segoe UI", 12, "bold"),
            foreground=TEXT_COLOR,
            background=DARK_BG
        )
        header_lbl.pack(pady=(15, 5), padx=20, anchor="w")
        
        sub_lbl = ttk.Label(
            self, 
            text="Choose one of the similar services found on your system:", 
            font=("Segoe UI", 10),
            foreground=TEXT_MUTED,
            background=DARK_BG
        )
        sub_lbl.pack(pady=(0, 15), padx=20, anchor="w")
        
        # Listbox Frame
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Scrollbars
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, 
            yscrollcommand=scrollbar.set, 
            bg=CARD_BG, 
            fg=TEXT_COLOR, 
            selectbackground=PRIMARY_COLOR, 
            selectforeground="#ffffff",
            font=("Segoe UI", 10),
            bd=0,
            highlightthickness=0
        )
        scrollbar.config(command=self.listbox.yview)
        
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        
        # Populate matching listbox
        for name, display in self.matches:
            self.listbox.insert(tk.END, f"{name}  —  ({display})")
            
        # Select first item
        self.listbox.selection_set(0)
        
        # Double click to select
        self.listbox.bind("<Double-Button-1>", lambda e: self.on_select())
        
        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", pady=20, padx=20)
        
        select_btn = ttk.Button(btn_frame, text="Select and Add", command=self.on_select)
        select_btn.pack(side="right", padx=(10, 0))
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", style="Danger.TButton", command=self.destroy)
        cancel_btn.pack(side="right")
        
        # Center in parent
        self.center_window(parent)
        
    def center_window(self, parent):
        self.update_idletasks()
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        x = parent_x + (parent_w - w) // 2
        y = parent_y + (parent_h - h) // 2
        self.geometry(f"+{x}+{y}")
        
    def on_select(self):
        selection = self.listbox.curselection()
        if selection:
            idx = selection[0]
            self.result = self.matches[idx][0] # Return the exact service name
        self.destroy()

class ServiceManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows Service Control Center")
        self.root.geometry("620x650")
        self.root.configure(bg=DARK_BG)
        
        # Load services
        self.services = self.load_services()
        if not self.services:
            self.services = ["W3SVC", "MSSQLSERVER"]
            self.save_services()

        # Track active background tasks to prevent race conditions
        self.running_tasks = set()

        self.setup_styles()
        self.build_ui()
        
        # System tray attributes
        self.tray_icon = None
        
        # Intercept the window close button
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        # Start periodic status auto-refresh (every 4000ms)
        self.schedule_auto_refresh()

    def setup_styles(self):
        """Configure a sleek modern dark mode theme using TTK."""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Base config
        style.configure(".", background=DARK_BG, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        
        # Frame styles
        style.configure("TFrame", background=DARK_BG)
        style.configure("Card.TFrame", background=CARD_BG, relief="flat")
        
        # Label styles
        style.configure("TLabel", background=DARK_BG, foreground=TEXT_COLOR)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground=TEXT_COLOR)
        style.configure("CardTitle.TLabel", background=CARD_BG, font=("Segoe UI", 11, "bold"), foreground=TEXT_COLOR)
        style.configure("Status.TLabel", background=CARD_BG, font=("Segoe UI", 9, "bold"))
        style.configure("Footer.TLabel", font=("Segoe UI", 9), foreground=TEXT_MUTED)

        # Button styles
        style.configure("TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none", relief="flat")
        style.map("TButton",
                  background=[("active", PRIMARY_HOVER), ("!disabled", PRIMARY_COLOR)],
                  foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")])
        
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none", relief="flat")
        style.map("Action.TButton",
                  background=[("active", PRIMARY_HOVER), ("!disabled", "#343444")],
                  foreground=[("active", "#ffffff"), ("!disabled", TEXT_COLOR)])

        style.configure("RowDelete.TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none", relief="flat")
        style.map("RowDelete.TButton",
                  background=[("active", ACCENT_RED), ("!disabled", "#343444")],
                  foreground=[("active", "#ffffff"), ("!disabled", TEXT_COLOR)])

        style.configure("Danger.TButton", font=("Segoe UI", 9, "bold"), borderwidth=0, focuscolor="none", relief="flat")
        style.map("Danger.TButton",
                  background=[("active", "#e03131"), ("!disabled", ACCENT_RED)],
                  foreground=[("active", "#ffffff"), ("!disabled", "#ffffff")])

        # Modern minimalist Scrollbar style
        style.configure("Vertical.TScrollbar", 
                        gripcount=0, 
                        background="#3b3b4f", 
                        troughcolor=DARK_BG, 
                        bordercolor=DARK_BG, 
                        lightcolor=DARK_BG, 
                        darkcolor=DARK_BG,
                        arrowcolor="#707080",
                        arrowsize=12)

        # Entry Style
        style.configure("TEntry", fieldbackground=CARD_BG, background=CARD_BG, foreground=TEXT_COLOR, borderwidth=0)

    def build_ui(self):
        # 1. Main Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill="x", padx=25, pady=20)
        
        title_label = ttk.Label(header_frame, text="Windows Service Manager", style="Header.TLabel")
        title_label.pack(side="left")
        
        admin_badge = ttk.Label(
            header_frame, 
            text="ADMIN MODE" if is_admin() else "LIMITED MODE", 
            foreground=ACCENT_GREEN if is_admin() else ACCENT_RED,
            font=("Segoe UI", 9, "bold")
        )
        admin_badge.pack(side="right", padx=5)

        # 2. Add Service Section
        add_frame = ttk.Frame(self.root)
        add_frame.pack(fill="x", padx=25, pady=5)
        
        # Modern bordered container mimicking premium Web CSS inputs
        self.entry_border = tk.Frame(add_frame, bg="#3b3b4f", bd=1)
        self.entry_border.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.service_entry = tk.Entry(
            self.entry_border, 
            font=("Segoe UI", 11),
            bg=CARD_BG,
            fg=TEXT_MUTED,
            insertbackground=TEXT_COLOR,
            relief="flat",
            bd=0
        )
        self.service_entry.pack(fill="x", ipady=6)
        self.service_entry.insert(0, "Enter Windows Service Name...")
        
        self.service_entry.bind("<FocusIn>", lambda e: self.on_entry_focus_in())
        self.service_entry.bind("<FocusOut>", lambda e: self.on_entry_focus_out())
        self.service_entry.bind("<Return>", lambda e: self.add_service())

        add_btn = ttk.Button(add_frame, text="Add Service", command=self.add_service)
        add_btn.pack(side="right", ipady=4)

        # 3. Global Action Buttons
        global_frame = ttk.Frame(self.root)
        global_frame.pack(fill="x", padx=25, pady=15)
        
        start_all_btn = ttk.Button(global_frame, text="▶ Start All Listed", command=self.start_all_services)
        start_all_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        stop_all_btn = ttk.Button(global_frame, text="⏹ Stop All Listed", command=self.stop_all_services)
        stop_all_btn.pack(side="left", fill="x", expand=True, padx=5)

        remove_all_btn = ttk.Button(global_frame, text="🗑 Clear All", style="Danger.TButton", command=self.remove_all_services)
        remove_all_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Divider
        divider = ttk.Separator(self.root, orient="horizontal")
        divider.pack(fill="x", padx=25, pady=10)

        # 4. Services List (With Scrollbar)
        list_container = ttk.Frame(self.root)
        list_container.pack(fill="both", expand=True, padx=25, pady=(5, 15))

        canvas = tk.Canvas(list_container, bg=DARK_BG, bd=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
        
        self.service_list_frame = ttk.Frame(canvas)
        self.service_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.service_list_frame, anchor="nw", width=550)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configure mousewheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # 5. Status / Footer Bar
        self.status_bar = ttk.Label(self.root, text="Ready", style="Footer.TLabel", anchor="w")
        self.status_bar.pack(fill="x", side="bottom", padx=25, pady=10)

        self.update_service_list()

    def set_status(self, text):
        """Update status bar text."""
        self.status_bar.config(text=text)

    def on_entry_focus_in(self):
        self.entry_border.config(bg=PRIMARY_COLOR)
        if self.service_entry.get() == "Enter Windows Service Name...":
            self.service_entry.delete(0, tk.END)
            self.service_entry.config(foreground=TEXT_COLOR)

    def on_entry_focus_out(self):
        self.entry_border.config(bg="#3b3b4f")
        if not self.service_entry.get().strip():
            self.service_entry.delete(0, tk.END)
            self.service_entry.insert(0, "Enter Windows Service Name...")
            self.service_entry.config(foreground=TEXT_MUTED)

    def clear_entry(self):
        self.service_entry.delete(0, tk.END)
        self.service_entry.insert(0, "Enter Windows Service Name...")
        self.service_entry.config(foreground=TEXT_MUTED)
        self.entry_border.config(bg="#3b3b4f")

    # --- System Tray Integration ---
    def hide_to_tray(self):
        """Minimize window to system tray icon instead of exiting."""
        self.root.withdraw()
        if not self.tray_icon:
            self.setup_tray()
        else:
            self.tray_icon.notify("Service Manager is running in hidden icons.", "Active Background Monitor")

    def create_tray_icon_image(self):
        """Generate a sleek, dark-theme circular icon programmatically using Pillow."""
        from PIL import Image, ImageDraw
        # Create a 64x64 transparent image
        img = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a beautiful smooth circular background using PRIMARY_COLOR (#4c6ef5)
        draw.ellipse([4, 4, 60, 60], fill=(76, 110, 245, 255))
        
        # Draw a high-contrast white gear-like core dot represent active status
        draw.ellipse([22, 22, 42, 42], fill=(255, 255, 255, 255))
        
        return img

    def setup_tray(self):
        """Initialize pystray icon and launch it in a separate daemon thread."""
        import pystray
        
        image = self.create_tray_icon_image()
        
        # Build dynamic context menu
        menu = pystray.Menu(
            pystray.MenuItem('Show Service Manager', self.restore_from_tray, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Exit Application', self.quit_application)
        )
        
        self.tray_icon = pystray.Icon("ServiceManager", image, "Windows Service Control Center", menu)
        
        # Launch tray loop in a background thread so it doesn't block Tkinter's event loop
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        
        # Show status notification balloon
        self.tray_icon.notify("Service Manager is running in hidden icons.", "Active Background Monitor")

    def restore_from_tray(self, icon=None, item=None):
        """Restore window from system tray and bring it to foreground."""
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.root.lift)
        self.root.after(0, self.root.focus_force)

    def quit_application(self, icon=None, item=None):
        """Fully clean up system tray hooks and exit the application."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.root.destroy)
        os._exit(0)

    # --- Data Persistence ---
    def get_services_filepath(self):
        """Retrieve the absolute path to services.txt in the user's AppData/Local folder."""
        appdata_path = os.environ.get("LOCALAPPDATA")
        if not appdata_path:
            return "services.txt"
        
        manager_dir = os.path.join(appdata_path, "ServiceManager")
        if not os.path.exists(manager_dir):
            try:
                os.makedirs(manager_dir, exist_ok=True)
            except Exception:
                return "services.txt"
                
        return os.path.join(manager_dir, "services.txt")

    def load_services(self):
        services = []
        filepath = self.get_services_filepath()
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as file:
                    services = [line.strip() for line in file.readlines() if line.strip()]
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load services: {e}")
        return services

    def save_services(self):
        try:
            filepath = self.get_services_filepath()
            with open(filepath, "w") as file:
                for service in self.services:
                    file.write(service + "\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save services: {e}")

    # --- Threaded Action Wrapper ---
    def run_in_thread(self, target_func, *args, **kwargs):
        """Utility to run commands asynchronously without blocking Tkinter."""
        thread = threading.Thread(target=target_func, args=args, kwargs=kwargs, daemon=True)
        thread.start()

    # --- Windows Command Execution ---
    def get_service_status(self, service_name):
        """Query service status safely."""
        try:
            # Query status via Windows SC command
            output = subprocess.check_output(
                ["sc", "query", service_name], 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if b"RUNNING" in output:
                return "running"
            elif b"STOPPED" in output:
                return "stopped"
            elif b"START_PENDING" in output:
                return "starting"
            elif b"STOP_PENDING" in output:
                return "stopping"
            else:
                return "stopped"
        except subprocess.CalledProcessError:
            return "not_found"

    def check_service_exists(self, service_name):
        """Validate if a service actually exists on Windows."""
        try:
            # sc query returncode is 1060 if service does not exist
            subprocess.check_output(
                ["sc", "query", service_name], 
                stderr=subprocess.STDOUT, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            return True
        except subprocess.CalledProcessError as e:
            if b"1060" in e.output: # Error code for service does not exist
                return False
            return True

    def get_all_windows_services(self):
        """Retrieve all Windows service names and display names."""
        services = []
        try:
            output = subprocess.check_output(
                ["sc", "query", "type=", "service", "state=", "all", "bufsize=", "1048576"],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            current_name = None
            for line in output.splitlines():
                line_str = line.decode('utf-8', errors='ignore').strip()
                if line_str.startswith("SERVICE_NAME:"):
                    current_name = line_str.split(":", 1)[1].strip()
                elif line_str.startswith("DISPLAY_NAME:") and current_name:
                    display_name = line_str.split(":", 1)[1].strip()
                    services.append((current_name, display_name))
                    current_name = None
        except Exception:
            try:
                output = subprocess.check_output(
                    ["sc", "query", "state=", "all"],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                current_name = None
                for line in output.splitlines():
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    if line_str.startswith("SERVICE_NAME:"):
                        current_name = line_str.split(":", 1)[1].strip()
                        services.append((current_name, current_name))
            except Exception:
                pass
        return services

    # --- UI Updating ---
    def update_service_list(self):
        """Rebuild the list display showing all services and their live states."""
        for widget in self.service_list_frame.winfo_children():
            widget.destroy()

        if not self.services:
            no_services_lbl = ttk.Label(
                self.service_list_frame, 
                text="No services listed. Enter a service name above to monitor.", 
                style="Footer.TLabel"
            )
            no_services_lbl.pack(pady=40, anchor="center")
            return

        for idx, service in enumerate(self.services):
            # Create a card frame for each service row with a sleek thin border
            card = tk.Frame(
                self.service_list_frame, 
                bg=CARD_BG, 
                highlightbackground="#353545", 
                highlightcolor="#353545", 
                highlightthickness=1, 
                bd=0
            )
            card.pack(fill="x", pady=6, padx=8)

            # Left Padding Frame inside card
            ttk.Frame(card, width=15, style="Card.TFrame").pack(side="left")

            # Service Label
            lbl = ttk.Label(card, text=service, style="CardTitle.TLabel", anchor="w")
            lbl.pack(side="left", fill="x", expand=True, pady=12)

            # Query Status
            status = self.get_service_status(service)
            
            # Badge formatting (pill/capsule style with subtle matching backgrounds)
            if status == "running":
                status_text = "● RUNNING"
                status_color = ACCENT_GREEN
                status_bg = "#162e24"
                btn_text = "⏹ Stop"
                btn_state = "normal"
            elif status == "stopped":
                status_text = "○ STOPPED"
                status_color = ACCENT_RED
                status_bg = "#34181a"
                btn_text = "▶ Start"
                btn_state = "normal"
            elif status in ["starting", "stopping"]:
                status_text = "⌛ PENDING"
                status_color = ACCENT_YELLOW
                status_bg = "#30230f"
                btn_text = "Processing..."
                btn_state = "disabled"
            else:
                status_text = "⚠ NOT FOUND"
                status_color = TEXT_MUTED
                status_bg = "#252530"
                btn_text = "▶ Start"
                btn_state = "disabled"

            status_lbl = tk.Label(
                card, 
                text=status_text, 
                font=("Segoe UI", 8, "bold"),
                fg=status_color,
                bg=status_bg,
                padx=10,
                pady=5
            )
            status_lbl.pack(side="left", padx=15)

            # Start/Stop Button
            toggle_btn = ttk.Button(
                card, 
                text=btn_text, 
                style="Action.TButton", 
                state=btn_state,
                command=lambda s=service: self.run_toggle_service(s)
            )
            toggle_btn.pack(side="left", padx=5)

            # Delete Button with custom hover styling
            remove_btn = ttk.Button(
                card, 
                text="🗑 Delete", 
                style="RowDelete.TButton", 
                command=lambda s=service: self.remove_service(s)
            )
            remove_btn.pack(side="left", padx=(5, 10))

    # --- Periodic Background Auto-Refresh ---
    def schedule_auto_refresh(self):
        """Schedule a background refresh of the service statuses."""
        if not self.running_tasks:  # Skip active UI rebuild if a start/stop is taking place
            self.run_in_thread(self._background_status_update)
        self.root.after(4000, self.schedule_auto_refresh)

    def _background_status_update(self):
        """Query statuses in background and update UI on main thread safely."""
        self.root.after(0, self.update_service_list)

    # --- Actions ---
    def add_service(self):
        service_name = self.service_entry.get().strip()
        if not service_name or service_name == "Enter Windows Service Name...":
            return

        if service_name in self.services:
            messagebox.showwarning("Warning", f"'{service_name}' is already in your monitor list.")
            return

        self.set_status(f"Verifying service '{service_name}'...")
        self.run_in_thread(self._async_add_service, service_name)

    def _async_add_service(self, service_name):
        exists = self.check_service_exists(service_name)
        if exists:
            self.services.append(service_name)
            self.save_services()
            self.root.after(0, self.update_service_list)
            self.root.after(0, self.clear_entry)
            self.root.after(0, lambda: self.set_status(f"Added service '{service_name}' successfully."))
            return

        # Service doesn't exist, search for matches
        self.root.after(0, lambda: self.set_status(f"Searching for services similar to '{service_name}'..."))
        all_services = self.get_all_windows_services()
        matches = []
        query_lower = service_name.lower()
        for name, display in all_services:
            if query_lower in name.lower() or query_lower in display.lower():
                matches.append((name, display))
        
        if matches:
            self.root.after(0, lambda: self.show_similarity_dialog(service_name, matches))
        else:
            self.root.after(0, lambda: self.show_not_found_dialog(service_name))

    def show_similarity_dialog(self, query, matches):
        dialog = ServiceChoiceDialog(self.root, query, matches)
        self.root.wait_window(dialog)
        
        selected_service = dialog.result
        if selected_service:
            if selected_service in self.services:
                messagebox.showwarning("Warning", f"'{selected_service}' is already in your monitor list.")
                self.set_status("Service already added.")
            else:
                self.services.append(selected_service)
                self.save_services()
                self.update_service_list()
                self.clear_entry()
                self.set_status(f"Added service '{selected_service}' successfully.")
        else:
            self.set_status("Adding service cancelled.")

    def show_not_found_dialog(self, service_name):
        confirm = messagebox.askyesno(
            "Service Not Found",
            f"Windows service '{service_name}' was not detected on this system.\n\n"
            "Do you want to add it to the monitoring list anyway?"
        )
        if confirm:
            self.services.append(service_name)
            self.save_services()
            self.update_service_list()
            self.clear_entry()
            self.set_status(f"Added service '{service_name}' successfully.")
        else:
            self.set_status("Cancelled adding service.")

    def remove_service(self, service_name):
        if messagebox.askyesno("Confirm Removal", f"Remove '{service_name}' from the monitoring list?"):
            self.services.remove(service_name)
            self.save_services()
            self.update_service_list()
            self.set_status(f"Removed service '{service_name}'.")

    def remove_all_services(self):
        if not self.services:
            return
        if messagebox.askyesnocancel("Confirm Clear All", "Are you sure you want to clear the entire monitoring list?"):
            self.services = []
            self.save_services()
            self.update_service_list()
            self.set_status("Cleared monitoring list.")

    def run_toggle_service(self, service_name):
        """Asynchronously triggers starting or stopping of a service."""
        if not is_admin():
            messagebox.showerror(
                "Privilege Required", 
                "Administrator privileges are required to change service states. Please restart the app as Administrator."
            )
            return
        
        self.running_tasks.add(service_name)
        self.update_service_list()
        self.set_status(f"Initiating state change for '{service_name}'...")
        self.run_in_thread(self._async_toggle_service, service_name)

    def _async_toggle_service(self, service_name):
        status = self.get_service_status(service_name)
        try:
            if status == "running":
                self.root.after(0, lambda: self.set_status(f"Stopping '{service_name}'..."))
                subprocess.run(["net", "stop", service_name], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
            elif status == "stopped":
                self.root.after(0, lambda: self.set_status(f"Starting '{service_name}'..."))
                subprocess.run(["net", "start", service_name], check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.CalledProcessError as e:
            self.root.after(0, lambda: messagebox.showerror("Operation Failed", f"Failed to toggle service '{service_name}':\nAccess Denied or invalid command execution."))
        
        self.running_tasks.remove(service_name)
        self.root.after(0, self.update_service_list)
        self.root.after(0, lambda: self.set_status("Operation complete."))

    # --- Global Command Actions ---
    def start_all_services(self):
        if not is_admin():
            messagebox.showerror("Privilege Required", "Admin privileges are required to start services.")
            return
        self.set_status("Starting all stopped services in the background...")
        self.run_in_thread(self._async_start_all)

    def _async_start_all(self):
        for service in self.services:
            if self.get_service_status(service) == "stopped":
                try:
                    subprocess.run(["net", "start", service], creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
        self.root.after(0, self.update_service_list)
        self.root.after(0, lambda: self.set_status("Finished attempting to start all services."))

    def stop_all_services(self):
        if not is_admin():
            messagebox.showerror("Privilege Required", "Admin privileges are required to stop services.")
            return
        self.set_status("Stopping all running services in the background...")
        self.run_in_thread(self._async_stop_all)

    def _async_stop_all(self):
        for service in self.services:
            if self.get_service_status(service) == "running":
                try:
                    subprocess.run(["net", "stop", service], creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass
        self.root.after(0, self.update_service_list)
        self.root.after(0, lambda: self.set_status("Finished attempting to stop all services."))

if __name__ == "__main__":
    # Check admin privileges. If not admin, warn the user and attempt to self-elevate
    if not is_admin():
        # Inform the user that they can run in limited viewer mode or elevate
        elevate = messagebox.askyesno(
            "Administrator Access Required",
            "This application needs Administrator privileges to start and stop services.\n\n"
            "Would you like to relaunch as Administrator now?"
        )
        if elevate:
            run_as_admin()
            sys.exit()
            
    root = tk.Tk()
    app = ServiceManagerApp(root)
    root.mainloop()
