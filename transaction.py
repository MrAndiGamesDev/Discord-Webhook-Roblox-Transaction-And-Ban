import os
import asyncio
import aiohttp
import signal
import sys
import json
from datetime import datetime
import pytz
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox
from threading import Thread
from alive_progress import alive_bar

# Load environment variables
load_dotenv()

# Configuration (initially empty)
DISCORD_WEBHOOK_URL = ""
USERID = ""
COOKIES = {}

TRANSACTION_API_URL = ""
CURRENCY_API_URL = ""

AVATAR_URL = "https://img.icons8.com/plasticine/2x/robux.png"  # Custom icon for Discord notification

UPDATEEVERY = 60  # Monitor interval

# Timezone setup
TIMEZONE = pytz.timezone("America/New_York")

# Graceful shutdown flag
shutdown_flag = False

# JSON storage paths
TRANSACTION_DATA_PATH = "transaction_data.json"
ROBUX_BALANCE_PATH = "robux_balance.json"

def signal_handler(signal, frame):
    """Handle graceful shutdown."""
    global shutdown_flag
    print("Shutting down...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)

def load_json_data(filepath, default_data):
    """Load data from a JSON file."""
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            return json.load(file)
    return default_data

def save_json_data(filepath, data):
    """Save data to a JSON file."""
    with open(filepath, 'w') as file:
        json.dump(data, file, indent=4)

def get_current_time():
    """Get the current time in the specified timezone (12-hour format)."""
    return datetime.now(TIMEZONE).strftime('%m/%d/%Y %I:%M:%S %p')

async def send_discord_notification(embed: dict):
    """Send a notification to the Discord webhook."""
    payload = {
        "embeds": [embed],
        "username": "Roblox Transaction Info",
        "avatar_url": AVATAR_URL
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30) as response:
                response.raise_for_status()
                print("Sent Discord notification successfully.")
        except aiohttp.ClientError as e:
            print(f"Error sending Discord notification: {e}")

async def send_discord_notification_for_changes(title: str, description: str, changes: dict, footer: str):
    """Send a notification for changes detected in transaction data."""
    fields = [{"name": key, "value": f"**{old}** → **{new}**", "inline": False} for key, (old, new) in changes.items()]
    embed = {
        "title": title,
        "description": description,
        "fields": fields,
        "color": 720640,
        "footer": {
            "text": footer
        }
    }
    await send_discord_notification(embed)

async def fetch_data(url: str):
    """Fetch data from the provided URL."""
    retries = 3
    async with aiohttp.ClientSession() as session:
        for _ in range(retries):
            try:
                async with session.get(url, cookies=COOKIES, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
            except aiohttp.ClientError as e:
                print(f"Failed to fetch data from {url}: {e}")
                await asyncio.sleep(5)
    return None

async def fetch_transaction_data():
    """Fetch transaction data."""
    return await fetch_data(TRANSACTION_API_URL)


async def fetch_robux_balance():
    """Fetch the current Robux balance."""
    response = await fetch_data(CURRENCY_API_URL)
    return response.get("robux", 0) if response else 0

async def monitor(gui_vars):
    """Monitor Roblox transaction and Robux data for changes."""
    last_transaction_data = load_json_data(TRANSACTION_DATA_PATH, {})
    last_robux_balance = load_json_data(ROBUX_BALANCE_PATH, {"robux": 0})

    iteration_count = 0

    # Using alive_bar with indefinite progress tracking
    with alive_bar(title="Monitoring Roblox Data", spinner="dots_waves") as bar:
        while not shutdown_flag:
            iteration_count += 1

            # Fetch transaction and balance data concurrently
            current_transaction_data, current_robux_balance = await asyncio.gather(
                fetch_transaction_data(),
                fetch_robux_balance()
            )

            # Update the GUI with the current balance
            gui_vars["robux_balance"].set(f"Current Robux Balance: {current_robux_balance}")

            # Check for changes in transaction data
            if current_transaction_data:
                changes = {
                    key: (last_transaction_data.get(key, 0), current_transaction_data[key])
                    for key in current_transaction_data if current_transaction_data[key] != last_transaction_data.get(key, 0)
                }

                if changes:
                    await send_discord_notification_for_changes(
                        "\U0001F514 Roblox Transaction Data Changed!",
                        f"Changes detected at {get_current_time()}",
                        changes,
                        f"Timestamp: {get_current_time()}"
                    )
                    last_transaction_data.update(current_transaction_data)
                    save_json_data(TRANSACTION_DATA_PATH, last_transaction_data)

            # Check for changes in Robux balance
            robux_change = current_robux_balance - last_robux_balance['robux']
            if robux_change != 0:
                color = 0x00FF00 if robux_change > 0 else 0xFF0000  # Green for gain, Red for spent
                change_type = "gained" if robux_change > 0 else "spent"
                await send_discord_notification({
                    "title": "\U0001F4B8 Robux Balance Update",
                    "description": f"You have **{change_type}** Robux.",
                    "fields": [
                        {"name": "Previous Balance", "value": f"**{last_robux_balance['robux']}**", "inline": True},
                        {"name": "Current Balance", "value": f"**{current_robux_balance}**", "inline": True},
                        {"name": "Change", "value": f"**{'+' if robux_change > 0 else ''}{robux_change}**", "inline": True}
                    ],
                    "color": color,
                    "footer": {"text": f"Change detected at {get_current_time()}"}
                })

                last_robux_balance['robux'] = current_robux_balance
                save_json_data(ROBUX_BALANCE_PATH, last_robux_balance)

            # Increment alive_bar to show activity
            bar()

            await asyncio.sleep(UPDATEEVERY)

def start_monitoring(gui_vars):
    """Start monitoring in a separate thread to avoid blocking the GUI."""
    global DISCORD_WEBHOOK_URL, USERID, COOKIES, TRANSACTION_API_URL, CURRENCY_API_URL

    # Get the values from the input fields
    DISCORD_WEBHOOK_URL = gui_vars["discord_webhook"].get()
    USERID = gui_vars["user_id"].get()
    COOKIES['.ROBLOSECURITY'] = gui_vars["roblox_cookies"].get()

    # Update the API URLs
    TRANSACTION_API_URL = f"https://economy.roblox.com/v2/users/{USERID}/transaction-totals?timeFrame=Year&transactionType=summary"
    CURRENCY_API_URL = f"https://economy.roblox.com/v1/users/{USERID}/currency"

    # Validate inputs
    if not DISCORD_WEBHOOK_URL or not USERID or not COOKIES['.ROBLOSECURITY']:
        messagebox.showerror("Error", "Please fill in all the fields!")
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(monitor(gui_vars))

def create_gui():
    """Create the GUI window and components."""
    root = tk.Tk()
    root.title("Roblox Monitoring")

    gui_vars = {
        "robux_balance": tk.StringVar(value="Current Robux Balance: 0"),
        "discord_webhook": tk.StringVar(),
        "user_id": tk.StringVar(),
        "roblox_cookies": tk.StringVar()
    }

    # Discord Webhook input field
    tk.Label(root, text="Discord Webhook URL").pack(pady=5)
    discord_webhook_entry = tk.Entry(root, textvariable=gui_vars["discord_webhook"], width=50)
    discord_webhook_entry.pack(pady=5)

    # User ID input field
    tk.Label(root, text="Roblox User ID").pack(pady=5)
    user_id_entry = tk.Entry(root, textvariable=gui_vars["user_id"], width=50)
    user_id_entry.pack(pady=5)

    # Roblox Cookies input field
    tk.Label(root, text="Roblox Cookies").pack(pady=5)
    roblox_cookies_entry = tk.Entry(root, textvariable=gui_vars["roblox_cookies"], width=50)
    roblox_cookies_entry.pack(pady=5)

    # Robux balance label
    robux_label = tk.Label(root, textvariable=gui_vars["robux_balance"], font=("Arial", 14))
    robux_label.pack(pady=20)

    # Start button
    start_button = tk.Button(root, text="Start Monitoring", command=lambda: Thread(target=start_monitoring, args=(gui_vars,)).start())
    start_button.pack(pady=10)

    # Stop button
    stop_button = tk.Button(root, text="Stop Monitoring", command=root.quit)
    stop_button.pack(pady=10)

    root.mainloop()

if __name__ == "__main__":
    try:
        create_gui()
    except KeyboardInterrupt:
        print("Script interrupted by user. Exiting...")
        sys.exit(0)
