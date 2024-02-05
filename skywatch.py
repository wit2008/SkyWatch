import requests
import fnmatch
import time
import csv
import os

# Add or remove these as needed
SQUAWK_MEANINGS = {
    "7500": "Aircraft Hijacking",
    "7600": "Radio Failure",
    "7700": "Emergency",
    "5000": "NORAD",
    "5400": "NORAD",
    "6100": "NORAD",
    "6400": "NORAD",
    "7777": "Millitary intercept",
    "0000": "discrete VFR operations",
    "1277": "Search & Rescue"
}

def load_env_file(file_path=".env"):
    with open(file_path) as file:
        for line in file:
            # Skip comments and empty lines
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value

load_env_file()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WATCHLIST_FILE = os.getenv("WATCHLIST_FILE")
AIRCRAFT_JSON_URI = os.getenv("AIRCRAFT_JSON_URI")
AIRCRAFT_CEILING = os.getenv("AIRCRAFT_CEILING")
ALTITUDE_FILTER = os.getenv("ALTITUDE_FILTER")
SCRIPT_INTERVAL = os.getenv("SCRIPT_INTERVAL")

def load_watchlist():
    watchlist = {}
    with open(WATCHLIST_FILE, "r") as file:
        for line in file:
            parts = line.split(':', 1)
            if len(parts) == 2:
                hex_code = parts[0].strip().upper()
                label = parts[1].strip()
                watchlist[hex_code] = label
    return watchlist


def send_telegram_alert(message):
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
    }
    response = requests.get(telegram_url, params=params)
    return response.status_code


def get_aircraft_data():
    url = AIRCRAFT_JSON_URI
    response = requests.get(url)
    data = response.json()
    return data['aircraft']


def load_csv_data(filename):
    csv_data = {}
    with open(filename, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            hex_code = row['$ICAO']
            csv_data[hex_code] = row
    return csv_data


def main():
    squawk_alert_history = {}
    watchlist_alert_history = {}
    csv_files = ["plane-alert-civ-images.csv", "plane-alert-mil-images.csv", "plane-alert-gov-images.csv"]
    csv_data = {}

    for filename in csv_files:
        csv_data.update(load_csv_data(filename))

    watchlist = load_watchlist()

    while True:
        aircraft_data = get_aircraft_data()

        for aircraft in aircraft_data:
            hex_code = aircraft['hex'].upper()
            flight = aircraft.get('flight', '').strip().upper()
            squawk = aircraft.get('squawk', '')
            altitude_geom = aircraft.get('alt_geom',0)
            altitude_baro = aircraft.get('alt_baro',0)

            # Alert on specific squawk codes
            if squawk in SQUAWK_MEANINGS and (
                    hex_code not in squawk_alert_history or time.time() - squawk_alert_history[hex_code] >= 3600):
                squawk_alert_history[hex_code] = time.time()
                squawk_meaning = SQUAWK_MEANINGS[squawk]

                if hex_code in csv_data:
                    context = csv_data[hex_code]
                    message = (
                        f"Squawk Alert!\nHex: {hex_code}\nSquawk: {squawk} ({squawk_meaning})\n"
                        f"Flight: {aircraft.get('flight', 'N/A')}\nAltitude: {aircraft.get('alt_geom', 'N/A')} ft\n"
                        f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\nTrack: {aircraft.get('track', 'N/A')}\n"
                        f"Operator: {context.get('$Operator', 'N/A')}\nType: {context.get('$Type', 'N/A')}\n"
                        f"Image: {context.get('#ImageLink', 'N/A')}"
                    )
                else:
                    message = (
                        f"Squawk Alert!\nHex: {hex_code}\nSquawk: {squawk} ({squawk_meaning})\n"
                        f"Flight: {aircraft.get('flight', 'N/A')}\nAltitude: {aircraft.get('alt_geom', 'N/A')} ft\n"
                        f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\nTrack: {aircraft.get('track', 'N/A')}"
                    )

                status_code = send_telegram_alert(message)
                if status_code == 200:
                    message_lines = message.split('\n')[:3]
                    for line in message_lines:
                        print(line)
                else:
                    print(f"Failed to send squawk alert. Status Code: {status_code}")

            # Alert on items in the watchlist
            for entry in watchlist:
                if (not ALTITUDE_FILTER or 
                    (ALTITUDE_FILTER and (int(altitude_geom != 0) and int(altitude_baro != 0)) and 
                     int(altitude_geom) <= int(AIRCRAFT_CEILING) and 
                     int(altitude_baro) <= int(AIRCRAFT_CEILING))):
                    if entry.endswith('*'):
                        if fnmatch.fnmatch(flight, entry):
                            if (hex_code not in watchlist_alert_history or
                                    time.time() - watchlist_alert_history[hex_code] >= 3600):
                                watchlist_alert_history[hex_code] = time.time()
                                if hex_code in csv_data:
                                    context = csv_data[hex_code]
                                    message = (
                                        f"Watchlist Alert!\n"
                                        f"Hex: {hex_code}\n"
                                        f"Label: {watchlist[entry]}\n"
                                        f"Flight: {aircraft.get('flight', 'N/A')}\n"
                                        f"Altitude (GEOM): {aircraft.get('alt_geom', 'N/A')} ft\n"
                                        f"Altitude (Baro): {aircraft.get('alt_baro', 'N/A')} ft\n"
                                        f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\n"
                                        f"Track: {aircraft.get('track', 'N/A')}\n"
                                        f"Operator: {context.get('$Operator', 'N/A')}\n"
                                        f"Type: {context.get('$Type', 'N/A')}\n"
                                        f"Image: {context.get('#ImageLink', 'N/A')}"
                                    )
                                else:
                                    message = (
                                        f"Watchlist Alert!\n"
                                        f"Hex: {hex_code}\n"
                                        f"Label: {watchlist[entry]}\n"
                                        f"Flight: {aircraft.get('flight', 'N/A')}\n"
                                        f"Altitude: {aircraft.get('alt_geom', 'N/A')} ft\n"
                                        f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\n"
                                        f"Track: {aircraft.get('track', 'N/A')}"
                                    )

                                status_code = send_telegram_alert(message)
                                if status_code == 200:
                                    message_lines = message.split('\n')[:3]
                                    for line in message_lines:
                                        print(line)
                                else:
                                    print(f"Failed to send watchlist alert. Status Code: {status_code}")
                    elif hex_code == entry or flight == entry:
                        if hex_code not in watchlist_alert_history or time.time() - watchlist_alert_history[hex_code] >= 3600:
                            watchlist_alert_history[hex_code] = time.time()
                            if hex_code in csv_data:
                                context = csv_data[hex_code]
                                message = (
                                    f"Watchlist Alert!\n"
                                    f"Hex: {hex_code}\n"
                                    f"Label: {watchlist[entry]}\n"
                                    f"Flight: {aircraft.get('flight', 'N/A')}\n"
                                    f"Altitude (GEOM): {aircraft.get('alt_geom', 'N/A')} ft\n"
                                    f"Altitude (Baro): {aircraft.get('alt_baro', 'N/A')} ft\n"
                                    f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\n"
                                    f"Track: {aircraft.get('track', 'N/A')}\n"
                                    f"Operator: {context.get('$Operator', 'N/A')}\n"
                                    f"Type: {context.get('$Type', 'N/A')}\n"
                                    f"Image: {context.get('#ImageLink', 'N/A')}"
                                )
                            else:
                                message = (
                                    f"Watchlist Alert!\nHex: {hex_code}\n"
                                    f"Label: {watchlist[entry]}\n"
                                    f"Flight: {aircraft.get('flight', 'N/A')}\n"
                                    f"Altitude (GEOM): {aircraft.get('alt_geom', 'N/A')} ft\n"
                                    f"Altitude (Baro): {aircraft.get('alt_baro', 'N/A')} ft\n"
                                    f"Ground Speed: {aircraft.get('gs', 'N/A')} knots\n"
                                    f"Track: {aircraft.get('track', 'N/A')}"
                                )

                            status_code = send_telegram_alert(message)
                            if status_code == 200:
                                message_lines = message.split('\n')[:3]
                                for line in message_lines:
                                    print(line)
                            else:
                                print(f"Failed to send watchlist alert. Status Code: {status_code}")

        time.sleep(SCRIPT_INTERVAL)


if __name__ == "__main__":
    main()
