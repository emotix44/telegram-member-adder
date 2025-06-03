import os
import time
import json
import csv
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telethon.errors import SessionPasswordNeededError, FloodWaitError

ACCOUNTS_DIR = 'accounts'
ADDED_TRACK_FILE = 'added_users.json'
USERS_CSV = 'users.csv'
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default = {"daily_limit": 40, "cooldown": 5}
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default, f)
        return default
    with open(CONFIG_FILE) as f:
        return json.load(f)

def save_added(phone, count):
    try:
        with open(ADDED_TRACK_FILE, 'r') as f:
            data = json.load(f)
    except:
        data = {}
    today = time.strftime('%Y-%m-%d')
    if today not in data:
        data[today] = {}
    data[today][phone] = count
    with open(ADDED_TRACK_FILE, 'w') as f:
        json.dump(data, f)

def get_added(phone):
    try:
        with open(ADDED_TRACK_FILE, 'r') as f:
            data = json.load(f)
    except:
        return 0
    today = time.strftime('%Y-%m-%d')
    return data.get(today, {}).get(phone, 0)

def get_accounts():
    return [f.replace('.session', '') for f in os.listdir(ACCOUNTS_DIR) if f.endswith('.session')]

def display_banner():
    os.system('clear')
    banner = """
\033[1;92m
 ████████╗███████╗██╗     ███████╗ █████╗  ██████╗ ████████╗
 ╚══██╔══╝██╔════╝██║     ██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝
    ██║   █████╗  ██║     █████╗  ███████║██║   ██║   ██║   
    ██║   ██╔══╝  ██║     ██╔══╝  ██╔══██║██║   ██║   ██║   
    ██║   ███████╗███████╗███████╗██║  ██║╚██████╔╝   ██║   
    ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝    ╚═╝   
\033[0m"""
    print(banner)

def load_users():
    with open(USERS_CSV, newline='') as f:
        return list(csv.reader(f))

def use_account(phone, config):
    api_id = int(input(f"Enter API ID for {phone}: "))
    api_hash = input(f"Enter API HASH for {phone}: ")
    client = TelegramClient(f'{ACCOUNTS_DIR}/{phone}', api_id, api_hash)
    client.connect()
    if not client.is_user_authorized():
        try:
            client.send_code_request(phone)
            code = input(f'Enter code for {phone}: ')
            client.sign_in(phone, code)
        except SessionPasswordNeededError:
            password = input(f"Two-step verification password for {phone}: ")
            client.sign_in(password=password)
    return client

def add_members(client, users, phone, config):
    daily_limit = config['daily_limit']
    cooldown = config['cooldown']
    added_count = get_added(phone)
    
    for user in users:
        if added_count >= daily_limit:
            print(f"[{phone}] Daily limit reached.")
            break
        name, number = user
        try:
            print(f"[{phone}] Adding {name} ({number})")
            contact = InputPhoneContact(client_id=0, phone=number, first_name=name, last_name="")
            result = client(ImportContactsRequest([contact]))
            added_count += 1
            save_added(phone, added_count)
            time.sleep(cooldown)
        except FloodWaitError as e:
            print(f"[{phone}] Flood wait: {e.seconds}s. Sleeping.")
            time.sleep(e.seconds)
        except Exception as e:
            print(f"[{phone}] Failed to add {name}: {e}")
            continue

def edit_or_delete_accounts():
    print("\nAccounts:")
    for i, acc in enumerate(get_accounts()):
        print(f"{i+1}. {acc}")
    choice = input("Enter number to delete or 'b' to go back: ")
    if choice.lower() == 'b':
        return
    try:
        index = int(choice) - 1
        acc = get_accounts()[index]
        os.remove(f"{ACCOUNTS_DIR}/{acc}.session")
        print(f"Deleted account {acc}")
    except:
        print("Invalid choice.")

def main_menu():
    config = load_config()
    display_banner()

    while True:
        print("\n[1] Add members\n[2] Add new account\n[3] Edit/Delete accounts\n[4] Exit")
        choice = input("Select: ")

        if choice == '1':
            users = load_users()
            for phone in get_accounts():
                try:
                    client = TelegramClient(f'{ACCOUNTS_DIR}/{phone}', 0, '')
                    client.connect()
                    add_members(client, users, phone, config)
                    client.disconnect()
                except Exception as e:
                    print(f"[{phone}] Error: {e}")
        elif choice == '2':
            phone = input("Enter new phone number (with country code): ")
            if not os.path.exists(ACCOUNTS_DIR):
                os.makedirs(ACCOUNTS_DIR)
            config = load_config()
            try:
                use_account(phone, config)
                print(f"Account {phone} added.")
            except Exception as e:
                print(f"Failed to add account: {e}")
        elif choice == '3':
            edit_or_delete_accounts()
        elif choice == '4':
            print("Exiting.")
            break
        else:
            print("Invalid choice.")

if __name__ == '__main__':
    main_menu()