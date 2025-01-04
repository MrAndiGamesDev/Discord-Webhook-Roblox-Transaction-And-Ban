import requests
import time
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DISCORD_WEBHOOK_URL = os.getenv("WEBHOOKURL2")
USERID = os.getenv("USERID")
TRANSACTION_API_URL = f"https://economy.roblox.com/v2/users/{USERID}/transaction-totals?timeFrame=Year&transactionType=summary"
CURRENCY_API_URL = f"https://economy.roblox.com/v1/users/{USERID}/currency"

TRANSACTION_DATA_FILE = "last_transaction_data.json"
ROBUX_FILE = "last_robux.json"

AVATAR_URL = "https://img.icons8.com/plasticine/2x/robux.png"

COOKIES = {
    '.ROBLOSECURITY': os.getenv("COOKIE"),
}

def load_json_file(file_path, default_data=None):
    """Load JSON data from a file or return default data if the file doesn't exist."""
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_data

def save_json_file(file_path, data):
    """Save JSON data to a file."""
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def load_last_transaction_data():
    """Load the last known transaction data from a file. Initialize with defaults if the file doesn't exist."""
    default_data = {key: 0 for key in [
        "salesTotal", "purchasesTotal", "affiliateSalesTotal", "groupPayoutsTotal",
        "currencyPurchasesTotal", "premiumStipendsTotal", "tradeSystemEarningsTotal",
        "tradeSystemCostsTotal", "premiumPayoutsTotal", "groupPremiumPayoutsTotal",
        "adSpendTotal", "developerExchangeTotal", "pendingRobuxTotal", "incomingRobuxTotal",
        "outgoingRobuxTotal", "individualToGroupTotal", "csAdjustmentTotal",
        "adsRevsharePayoutsTotal", "groupAdsRevsharePayoutsTotal", "subscriptionsRevshareTotal",
        "groupSubscriptionsRevshareTotal", "subscriptionsRevshareOutgoingTotal",
        "groupSubscriptionsRevshareOutgoingTotal", "publishingAdvanceRebatesTotal",
        "affiliatePayoutTotal"
    ]}
    return load_json_file(TRANSACTION_DATA_FILE, default_data)

def load_last_robux():
    """Load the last known Robux balance from a separate file."""
    return load_json_file(ROBUX_FILE, {"robux": 0}).get("robux", 0)

def send_discord_notification(embed):
    """Send a notification to the Discord webhook."""
    payload = {
        "embeds": [embed],
        "username": "Roblox Transaction Info",
        "avatar_url": f"{AVATAR_URL}"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Discord notification: {e}")

def send_discord_notification_for_changes(title, description, changes, footer):
    """Send a notification to the Discord webhook for data changes."""
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
    send_discord_notification(embed)

def fetch_data(url):
    """Fetch data from a given URL with cookies."""
    try:
        response = requests.get(url, cookies=COOKIES, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch data from {url}: {e}")
        return None

def fetch_transaction_data():
    """Fetch transaction data from the API."""
    return fetch_data(TRANSACTION_API_URL)

def fetch_robux_balance():
    """Fetch Robux balance from the currency API."""
    return fetch_data(CURRENCY_API_URL).get("robux", 0)

def monitor():
    """Monitor the APIs for changes."""
    last_transaction_data = load_last_transaction_data()
    last_robux = load_last_robux()

    while True:
        current_transaction_data = fetch_transaction_data()
        current_robux_balance = fetch_robux_balance()

        if current_transaction_data:
            changes = {
                key: (last_transaction_data.get(key), current_transaction_data[key])
                for key in current_transaction_data
                if current_transaction_data[key] != last_transaction_data.get(key)
            }

            if changes:
                send_discord_notification_for_changes(
                    "🔔Roblox Transaction Data Changed!",
                    "The following changes were detected:",
                    changes,
                    ""
                )
                last_transaction_data.update(current_transaction_data)
                save_json_file(TRANSACTION_DATA_FILE, last_transaction_data)

        if current_robux_balance != last_robux:
            send_discord_notification_for_changes(
                "🔔Robux Balance Changed!",
                f"**Robux:** **{last_robux}** → **{current_robux_balance}**",
                {},
                "Transaction Fetched From Roblox's API"
            )
            last_robux = current_robux_balance
            save_json_file(ROBUX_FILE, {"robux": last_robux})

        time.sleep(60)  # Check every 60 seconds

if __name__ == "__main__":
    while True:
        monitor()  # Start monitoring without an infinite loop
        time.sleep(10)