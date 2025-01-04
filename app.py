import subprocess
import tkinter as tk
import os
import sqlite3
from datetime import datetime

class RobloxTransactionApp:
    def __init__(self, master):
        self.master = master
        self.appversion = "V0.3.0"
        master.title(f"Roblox Transaction Monitor")
        master.geometry("400x300")  # Set a larger size for the GUI

        # Initialize the database
        self.db_path = "transaction_app.db"
        self.init_db()

        self.label = tk.Label(master, text=f"Roblox Transaction Monitor {self.appversion}", font=("Arial", 16))
        self.label.pack(pady=10)

        self.start_button = tk.Button(master, text="Start Monitoring", command=self.start_monitoring, width=20, font=("Arial", 12), relief="raised")
        self.start_button.pack(pady=5)

        self.stop_button = tk.Button(master, text="Stop Monitoring", command=self.stop_monitoring, width=20, font=("Arial", 12), relief="raised")
        self.stop_button.pack(pady=5)

        self.theme_button = tk.Button(master, text="Toggle Theme", command=self.toggle_theme, width=20, font=("Arial", 12), relief="raised")
        self.theme_button.pack(pady=5)

        self.status_label = tk.Label(master, text="Status: Not Monitoring", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.monitoring = False
        self.dark_theme = True  # Default to dark theme

        self.apply_theme()  # Apply the initial theme

    def init_db(self):
        """Initialize the SQLite database and create necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Create monitoring status table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT,
                    timestamp TEXT
                )
            """)
            # Create action log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def log_action(self, action):
        """Log an action (start/stop) to the database."""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO action_log (action, timestamp)
                VALUES (?, ?)
            """, (action, timestamp))
            conn.commit()

    def start_monitoring(self):
        if not self.monitoring:
            self.monitoring = True
            self.status_label.config(text="Status: Monitoring...")
            self.log_action("Started monitoring")

            # List of script names to be monitored
            scripts = ['ban.py', 'transaction.py']
            
            # Start monitoring each script using a for loop
            for script in scripts:
                subprocess.Popen(['python', script])

            # Update monitoring status in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO monitoring_status (status, timestamp)
                    VALUES (?, ?)
                """, ("Monitoring", datetime.now().isoformat()))
                conn.commit()

    def stop_monitoring(self):
        if self.monitoring:
            self.monitoring = False
            self.status_label.config(text="Status: Not Monitoring")
            self.log_action("Stopped monitoring")

            # Update monitoring status in database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO monitoring_status (status, timestamp)
                    VALUES (?, ?)
                """, ("Not Monitoring", datetime.now().isoformat()))
                conn.commit()

            self.master.quit()  # Exit the application

    def toggle_theme(self):
        self.dark_theme = not self.dark_theme
        self.apply_theme()

    def match_system_theme(self):
        try:
            if os.name == 'nt':  # Windows system
                import ctypes
                dark_mode = ctypes.windll.dwmapi.DwmGetColorizationParameters().ColorizationColor >> 24 < 128
                return dark_mode
            else:
                # For other systems, assume light theme by default
                return False
        except:
            return False

    def apply_theme(self):
        if self.dark_theme:
            self.master.config(bg="black")
            self.label.config(bg="black", fg="white")
            self.status_label.config(bg="black", fg="white")
            button_bg = "#555555"
            button_fg = "white"
        else:
            self.master.config(bg="white")
            self.label.config(bg="white", fg="black")
            self.status_label.config(bg="white", fg="black")
            button_bg = "#4CAF50"
            button_fg = "white"

        self.start_button.config(bg=button_bg, fg=button_fg)
        self.stop_button.config(bg=button_bg, fg=button_fg)
        self.theme_button.config(bg=button_bg, fg=button_fg)

if __name__ == "__main__":
    root = tk.Tk()
    app = RobloxTransactionApp(root)
    root.mainloop()