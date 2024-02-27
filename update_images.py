import os
import urllib.request


def load_env_file(file_path=".env"):
    with open(file_path) as file:
        for line in file:
            # Skip comments and empty lines
            if line.strip() and not line.startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ[key] = value


load_env_file()

IMAGE_FILES = os.getenv("IMAGE_FILES").split(",")

URL_BASE = "https://raw.githubusercontent.com/sdr-enthusiasts/plane-alert-db/main/"

# Prompt for confirmation
confirmation = input(
    "Are you sure you want to rename and download the files? (y/n): ")
if confirmation.lower() != "y":
    print("Exiting...")
    exit()

for file in IMAGE_FILES:
    file_path = os.path.join(os.getcwd(), file)
    new_file_path = file_path + ".old"

    # Rename the existing file (force if it exists)
    if os.path.exists(file_path):
        os.replace(file_path, new_file_path)

    # Download the fresh copy
    url = URL_BASE + file
    urllib.request.urlretrieve(url, file_path)
