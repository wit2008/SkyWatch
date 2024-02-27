import os
import csv
import requests


def load_env_file(file_path=".env"):
    with open(file_path) as file:
        for line in file:
            # Skip comments and empty lines
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


load_env_file()

LIST_FILES = os.getenv("LIST_FILES").split(",")
WATCHLIST_FILE = os.getenv("WATCHLIST_FILE")

URL_BASE = "https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/"

# Prompt for confirmation
confirmation = input(
    "Are you sure you want to rename and download the files? (y/n): ")
if confirmation.lower() != "y":
    print("Exiting...")
    exit()

if os.path.exists(WATCHLIST_FILE):
    os.replace(WATCHLIST_FILE, WATCHLIST_FILE + ".old")

# Download CSV files
for file in LIST_FILES:
    url = URL_BASE + file
    response = requests.get(url)
    with open(file, "wb") as csv_file:
        csv_file.write(response.content)

# Process CSV data and write to watchlist
with open(WATCHLIST_FILE, "w", encoding="utf-8") as output_file:
    for file in LIST_FILES:
        with open(file, "r", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                icao = row["$ICAO"]
                operator = row["$Operator"]
                aircraft_type = row["$Type"]
                tag1 = row["$Tag 1"]
                tag2 = row["$#Tag 2"]
                tag3 = row["$#Tag 3"]
                combined_tags = f"{tag1} {tag2} {tag3}"
                if combined_tags == "None None None":
                    combined_data = f"{operator} {aircraft_type}"
                else:
                    combined_data = f"{operator} {aircraft_type} Tags: {tag1}, {tag2}, {tag3}"

                if combined_data == "None None":
                    combined_data = "Unknown or Private ICAO"
                processed_row = f"{icao}: {combined_data}"
                output_file.write(processed_row + "\n")

# Clean up downloaded files
for file in LIST_FILES:
    os.remove(file)
