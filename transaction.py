import os
import asyncio
import sqlite3
import aiohttp
import signal
import sys
from datetime import datetime
import pytz
from dotenv import load_dotenv

load_dotenv()

# Configuration
DISCORD_WEBHOOK_URL = os.getenv("WEBHOOKURL2")
USERID = os.getenv("USERID")
TRANSACTION_API_URL = f"https://economy.roblox.com/v2/users/{USERID}/transaction-totals?timeFrame=Year&transactionType=summary"
CURRENCY_API_URL = f"https://economy.roblox.com/v1/users/{USERID}/currency"

AVATAR_URL = "https://img.icons8.com/plasticine/2x/robux.png"  # Custom icon for Discord notification
COOKIES = {
    '.ROBLOSECURITY': os.getenv("COOKIE"),
}

# Timezone setup
TIMEZONE = pytz.timezone("America/New_York")

# Graceful shutdown flag
shutdown_flag = False

# Database setup
DATABASE_PATH = "roblox_monitor.db"

def init_db():
    """Initialize SQLite database and create necessary tables."""
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transaction_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salesTotal INTEGER, purchasesTotal INTEGER, affiliateSalesTotal INTEGER,
                groupPayoutsTotal INTEGER, currencyPurchasesTotal INTEGER, premiumStipendsTotal INTEGER,
                tradeSystemEarningsTotal INTEGER, tradeSystemCostsTotal INTEGER, premiumPayoutsTotal INTEGER,
                groupPremiumPayoutsTotal INTEGER, adSpendTotal INTEGER, developerExchangeTotal INTEGER,
                pendingRobuxTotal INTEGER, incomingRobuxTotal INTEGER, outgoingRobuxTotal INTEGER,
                individualToGroupTotal INTEGER, csAdjustmentTotal INTEGER, adsRevsharePayoutsTotal INTEGER,
                groupAdsRevsharePayoutsTotal INTEGER, subscriptionsRevshareTotal INTEGER,
                groupSubscriptionsRevshareTotal INTEGER, subscriptionsRevshareOutgoingTotal INTEGER,
                groupSubscriptionsRevshareOutgoingTotal INTEGER, publishingAdvanceRebatesTotal INTEGER,
                affiliatePayoutTotal INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS robux_balance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robux INTEGER
            )
        """)
        conn.commit()

def signal_handler(signal, frame):
    """Handle graceful shutdown."""
    global shutdown_flag
    print("Shutting down...")
    shutdown_flag = True

signal.signal(signal.SIGINT, signal_handler)

async def load_last_data(table: str, columns: list):
    """Load the last row of data from the given table and columns."""
    query = f"SELECT * FROM {table} ORDER BY id DESC LIMIT 1"
    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        row = cursor.fetchone()

    if row:
        return {columns[i]: row[i + 1] for i in range(len(columns))}
    else:
        return {column: 0 for column in columns}

async def save_data(table: str, data: dict):
    """Save data to the specified table."""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

    with sqlite3.connect(DATABASE_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(query, tuple(data.values()))
        conn.commit()

async def send_discord_notification(embed: dict):
    """Send a notification to the Discord webhook."""
    payload = {
        "embeds": [embed],
        "username": "Roblox Transaction Info",
        "avatar_url": AVATAR_URL  # Include custom avatar URL
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
    return (await fetch_data(CURRENCY_API_URL)).get("robux", 0)

def get_current_time():
    """Get the current time in the specified timezone (12-hour format)."""
    return datetime.now(TIMEZONE).strftime('%m/%d/%Y %I:%M:%S %p')

async def monitor():
    """Monitor Roblox transaction and Robux data for changes."""
    last_transaction_columns = [
        "salesTotal", "purchasesTotal", "affiliateSalesTotal", "groupPayoutsTotal", "currencyPurchasesTotal",
        "premiumStipendsTotal", "tradeSystemEarningsTotal", "tradeSystemCostsTotal", "premiumPayoutsTotal",
        "groupPremiumPayoutsTotal", "adSpendTotal", "developerExchangeTotal", "pendingRobuxTotal", "incomingRobuxTotal",
        "outgoingRobuxTotal", "individualToGroupTotal", "csAdjustmentTotal", "adsRevsharePayoutsTotal",
        "groupAdsRevsharePayoutsTotal", "subscriptionsRevshareTotal", "groupSubscriptionsRevshareTotal",
        "subscriptionsRevshareOutgoingTotal", "groupSubscriptionsRevshareOutgoingTotal", "publishingAdvanceRebatesTotal",
        "affiliatePayoutTotal"
    ]

    last_transaction_data = await load_last_data("transaction_data", last_transaction_columns)
    last_robux = await load_last_data("robux_balance", ["robux"])

    while not shutdown_flag:
        current_transaction_data, current_robux_balance = await asyncio.gather(
            fetch_transaction_data(),
            fetch_robux_balance()
        )

        if current_transaction_data:
            changes = {key: (last_transaction_data.get(key), current_transaction_data[key])
                       for key in current_transaction_data if current_transaction_data[key] != last_transaction_data.get(key)}

            if changes:
                await send_discord_notification_for_changes(
                    "🔔Roblox Transaction Data Changed!",
                    f"Changes detected at {get_current_time()}",
                    changes,
                    f"Timestamp: {get_current_time()}"
                )
                last_transaction_data.update(current_transaction_data)
                await save_data("transaction_data", current_transaction_data)

        if current_robux_balance != last_robux['robux']:
            await send_discord_notification_for_changes(
                "🔔Robux Balance Changed!",
                f"**Robux:** **{last_robux['robux']}** → **{current_robux_balance}**\n"
                f"**Change detected at {get_current_time()}**",
                {},
                "Transaction Fetched From Roblox's API"
            )
            last_robux['robux'] = current_robux_balance
            await save_data("robux_balance", {"robux": last_robux['robux']})

        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        init_db()
        asyncio.run(monitor())
    except KeyboardInterrupt:
        print("Script interrupted by user. Exiting...")
        sys.exit(0)