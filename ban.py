import requests
import time
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

class DiscordNotifier:
    def __init__(self, webhook_url, roblox_security, api_url, db_path):
        self.webhook_url = webhook_url
        self.roblox_security = roblox_security
        self.api_url = api_url
        self.db_path = db_path
        self.cookie = os.getenv("COOKIE")
        self.headers = {
            "Cookie": f"{self.roblox_security}{self.cookie}"
        }
        self.init_db()  # Initialize database

    def init_db(self):
        """Initialize the SQLite database and create necessary tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
                CREATE TABLE IF NOT EXISTS moderation_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    messageToUser TEXT,
                    punishmentTypeDescription TEXT,
                    beginDate TEXT,
                    endDate TEXT,
                    next_consequence_duration INTEGER,
                    next_consequence_type TEXT,
                    self_service_deactivated BOOLEAN,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def load_last_data(self):
        """Load the last known data from the database."""
        query = "SELECT * FROM moderation_data ORDER BY timestamp DESC LIMIT 1"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            row = cursor.fetchone()

        if row:
            return {
                "messageToUser": row[1],
                "punishmentTypeDescription": row[2],
                "beginDate": row[3],
                "endDate": row[4],
                "next_consequence_duration": row[5],
                "next_consequence_type": row[6],
                "self_service_deactivated": row[7],
                "timestamp": row[8]
            }
        else:
            print("Starting with no previous data.")
            return None

    def save_last_data(self, data):
        """Save the current data to the database."""
        timestamp = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
                INSERT INTO moderation_data (
                    messageToUser, punishmentTypeDescription, beginDate, endDate, 
                    next_consequence_duration, next_consequence_type, 
                    self_service_deactivated, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("messageToUser", "N/A"),
                data.get("punishmentTypeDescription", "N/A"),
                data.get("beginDate", "N/A"),
                data.get("endDate", "N/A"),
                data.get("context", {}).get("NEXT_CONSEQUENCE_DURATION", "N/A"),
                data.get("context", {}).get("NEXT_CONSEQUENCE_TYPE", "N/A"),
                data.get("context", {}).get("SelfServiceDeactivated", False),
                timestamp
            ))
            conn.commit()

    @staticmethod
    def discord_timestamp(utc_time_str):
        """Convert a UTC time string to a Discord timestamp."""
        if not utc_time_str:
            return "Unknown"
        try:
            # Parse the UTC time string, replacing 'Z' with '+00:00' for ISO format compatibility
            utc_time = datetime.fromisoformat(utc_time_str.replace("Z", "+00:00"))
            # Adjust to the desired timezone (UTC-05:00)
            adjusted_time = utc_time + timedelta(hours=0)
            # Convert to a Unix timestamp
            unix_timestamp = int(adjusted_time.timestamp())
            # Return a relative time string for Discord and a formatted time
            return f"<t:{unix_timestamp}:R> (<t:{unix_timestamp}:F>)"
        except ValueError:
            return "Invalid Timestamp"

    def fetch_data(self):
        """Fetch moderation data from the Roblox API."""
        try:
            response = requests.get(self.api_url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch data: {e}")
            self.send_error_to_discord(f"Error fetching data: {e}")  # Send error to Discord
            return None

    def send_to_discord(self, data):
        """Send extracted data to Discord via webhook."""
        try:
            embed = self.create_embed(data)
            response = requests.post(self.webhook_url, json=embed)
            response.raise_for_status()
            print("Message sent successfully to Discord!")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send message to Discord: {e}")
            self.send_error_to_discord(f"Error sending message to Discord: {e}")  # Send error to Discord

    def send_error_to_discord(self, error_message):
        """Send an error message to Discord via webhook."""
        timestamp = datetime.now().isoformat() + "Z"
        error_embed = {
            "username": "Error Alert",
            "embeds": [
                {
                    "title": "Error Occurred",
                    "color": 16711680,
                    "fields": [
                        {"name": "Error Message", "value": error_message, "inline": False},
                        {"name": "Timestamp", "value": timestamp, "inline": False},
                    ],
                    "footer": {
                        "text": "Error Notification",
                    }
                }
            ]
        }
        try:
            response = requests.post(self.webhook_url, json=error_embed)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to send error to Discord: {e}")

    def create_embed(self, data):
        """Create a Discord embed from the moderation data."""
        return {
            "avatar_url": "https://www.pngmart.com/files/23/Ban-Hammer-PNG-179x200.png",
            "username": "Moderation Alert",
            "embeds": [
                {
                    "title": "🔨Moderation Action Taken",
                    "color": 16711680,
                    "fields": [
                        {"name": "Message To User", "value": data.get("messageToUser", "N/A"), "inline": False},
                        {"name": "Punishment", "value": data.get("punishmentTypeDescription", "N/A"), "inline": True},
                        {"name": "Begin Date", "value": self.discord_timestamp(data.get("beginDate", "N/A")), "inline": True},
                        {"name": "End Date", "value": self.discord_timestamp(data.get("endDate", "N/A")), "inline": True},
                        {"name": "Next Consequence Duration", "value": f"{data['context'].get('NEXT_CONSEQUENCE_DURATION', 'N/A')} days", "inline": True},
                        {"name": "Next Consequence Type", "value": data['context'].get("NEXT_CONSEQUENCE_TYPE", "N/A"), "inline": True},
                        {"name": "Reactivation Support", "value": data['context'].get("SelfServiceDeactivated", "False"), "inline": True},  # Added reactivation support
                    ],
                    "footer": {
                        "text": "Moderation Fetched From Roblox's API",
                    }
                }
            ]
        }

    def process_data(self):
        """Main loop to fetch and process data."""
        last_data = self.load_last_data()

        while True:
            data = self.fetch_data()
            if data and data != last_data:
                self.send_to_discord(data)
                self.save_last_data(data)
                last_data = data
            time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # Replace with your Discord webhook URL, .ROBLOSECURITY cookie, and database path
    notifier = DiscordNotifier(
        webhook_url=os.getenv("WEBHOOKURL"),
        roblox_security=".ROBLOSECURITY=",
        api_url="https://usermoderation.roblox.com/v1/not-approved",
        db_path="moderation_data.db"  # SQLite database path
    )
    
    while True:  # Run forever
        notifier.process_data()
        time.sleep(10)  # Optional sleep to prevent tight looping