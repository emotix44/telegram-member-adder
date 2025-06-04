import asyncio
import json
import os
import datetime
import sys
import time
import threading
import requests
from telethon import TelegramClient, errors
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import ChannelParticipantsRecent
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich import box

# Constants
KILL_SWITCH_URL = "https://raw.githubusercontent.com/emotix44/telegram-member-adder/main/switch.txt"
CONFIG_FILE = "config.json"
ACCOUNTS_FILE = "accounts.json"
PROGRESS_FILE = "progress.json"
MESSAGING_FILE = "messaging.json"
SESSIONS_DIR = "sessions"
CHECK_INTERVAL = 10  # seconds

# Banner
BANNER = """
[bold dark_orange]
 ███╗   ███╗███████╗███╗   ███╗██████╗ ███████╗██████╗     █████╗ ██████╗ ██████╗ ███████╗██████╗
 ████╗ ████║██╔════╝████╗ ████║██╔══██╗██╔════╝██╔══██╗   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ██╔████╔██║█████╗  ██╔████╔██║██████╔╝█████╗  ██████╔╝   ███████║██║  ██║██║  ██║█████╗  ██████╔╝
 ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══██╗   ██╔══██║██║  ██║██║  ██║██╔══╝  ██╔══██╗
 ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║██║  ██║███████╗██║  ██║██╗██║  ██║██████╔╝██████╔╝███████╗██║  ██║
 ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
[/bold dark_orange]
"""

# ========== Remote Kill Switch ==========
def check_status_online():
    try:
        url = 'https://raw.githubusercontent.com/emotix44/telegram-member-adder/main/status.txt'
        response = requests.get(url)
        if response.status_code == 200:
            if response.text.strip().lower() == 'off':
                print("\n🛑 Script is disabled by owner. Exiting...")
                exit()
            else:
                print("✅ Remote switch is ON. Continuing...\n")
        else:
            print(f"⚠️ Failed to fetch remote status. HTTP {response.status_code}")
    except Exception as e:
        print(f"⚠️ Error checking remote status: {e}")

check_status_online()

# ========== Local Kill Switch Monitor ==========
class KillSwitchMonitor(threading.Thread):
    def __init__(self, filename='kill_switch.txt'):
        super().__init__()
        self.filename = filename
        self.running = True

    def run(self):
        while self.running:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    status = f.read().strip().lower()
                    if status == 'off':
                        print("\n🛑 Local kill switch activated. Exiting...")
                        os._exit(1)
            time.sleep(5)

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return self.create_new_config()
        with open(CONFIG_FILE) as f:
            return json.load(f)
    
    def create_new_config(self):
        config = {
            "source_group": input("Enter source group username (with @): "),
            "dest_group": input("Enter destination group username (with @): "),
            "limit_per_day": int(input("Daily member limit per account: ")),
            "delay_between_adds": 10,
            "message_delay": 5,
            "message_limit": 20
        }
        self.save_config(config)
        return config
    
    def save_config(self, config=None):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config or self.config, f, indent=2)
    
    def reset_daily_counters(self):
        today = datetime.date.today().isoformat()
        if self.config.get("last_run_date") != today:
            progress_manager = ProgressManager()
            progress_manager.reset_all_progress()
            
            # Reset messaging counters
            messaging_manager = MessagingManager()
            for session in messaging_manager.stats:
                messaging_manager.stats[session]["sent"] = 0
            messaging_manager.save_stats()
            
            self.config["last_run_date"] = today
            self.save_config()
            return True
        return False

class AccountManager:
    def __init__(self):
        self.accounts = self.load_accounts()
        
    def load_accounts(self):
        if not os.path.exists(ACCOUNTS_FILE):
            return []
        with open(ACCOUNTS_FILE) as f:
            return json.load(f)
    
    def save_accounts(self):
        with open(ACCOUNTS_FILE, "w") as f:
            json.dump(self.accounts, f, indent=2)
    
    def add_account(self, api_id, api_hash, session_name):
        if any(acc["session_name"] == session_name for acc in self.accounts):
            return False
        self.accounts.append({
            "api_id": api_id,
            "api_hash": api_hash,
            "session_name": session_name
        })
        self.save_accounts()
        return True
    
    def remove_account(self, index):
        if 0 <= index < len(self.accounts):
            account = self.accounts.pop(index)
            # Clean up related files
            progress_manager = ProgressManager()
            progress_manager.remove_account_progress(account["session_name"])
            
            # Remove from messaging stats
            messaging_manager = MessagingManager()
            if account["session_name"] in messaging_manager.stats:
                del messaging_manager.stats[account["session_name"]]
                messaging_manager.save_stats()
            
            # Remove session file
            session_file = f"{SESSIONS_DIR}/{account['session_name']}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
                
            self.save_accounts()
            return True
        return False

class ProgressManager:
    def __init__(self):
        self.progress = self.load_progress()
        
    def load_progress(self):
        if not os.path.exists(PROGRESS_FILE):
            return {}
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    
    def save_progress(self):
        with open(PROGRESS_FILE, "w") as f:
            json.dump(self.progress, f)
    
    def get_progress(self, session_name):
        return self.progress.get(session_name, 0)
    
    def set_progress(self, session_name, value):
        self.progress[session_name] = value
        self.save_progress()
    
    def reset_account_progress(self, session_name):
        if session_name in self.progress:
            self.progress[session_name] = 0
            self.save_progress()
    
    def reset_all_progress(self):
        self.progress = {}
        self.save_progress()
    
    def remove_account_progress(self, session_name):
        if session_name in self.progress:
            del self.progress[session_name]
            self.save_progress()

class MessagingManager:
    def __init__(self):
        self.stats = self.load_stats()
        
    def load_stats(self):
        if not os.path.exists(MESSAGING_FILE):
            return {}
        with open(MESSAGING_FILE) as f:
            return json.load(f)
    
    def save_stats(self):
        with open(MESSAGING_FILE, "w") as f:
            json.dump(self.stats, f)
    
    def get_account_stats(self, session_name):
        return self.stats.get(session_name, {"sent": 0, "last_target": ""})
    
    def update_account_stats(self, session_name, target_group, sent_count):
        if session_name not in self.stats:
            self.stats[session_name] = {"sent": 0, "last_target": ""}
            
        self.stats[session_name]["sent"] += sent_count
        self.stats[session_name]["last_target"] = target_group
        self.save_stats()
    
    def reset_account_stats(self, session_name):
        if session_name in self.stats:
            self.stats[session_name]["sent"] = 0
            self.save_stats()

class TelegramOperations:
    def __init__(self, console):
        self.console = console
        self.config_manager = ConfigManager()
        self.account_manager = AccountManager()
        self.progress_manager = ProgressManager()
        self.messaging_manager = MessagingManager()
        
    async def add_members(self, account):
        session_name = account["session_name"]
        try:
            async with TelegramClient(
                f"{SESSIONS_DIR}/{session_name}",
                account["api_id"],
                account["api_hash"]
            ) as client:
                # Get entities
                source = await client.get_entity(self.config_manager.config["source_group"])
                dest = await client.get_entity(self.config_manager.config["dest_group"])
                
                # Get existing members
                existing_members = await client.get_participants(dest)
                existing_ids = {u.id for u in existing_members}
                
                # Get all participants
                all_participants = await client.get_participants(source, filter=ChannelParticipantsRecent())
                start_index = self.progress_manager.get_progress(session_name)
                count = 0
                total = len(all_participants) - start_index
                
                if total <= 0:
                    self.console.print(f"[yellow]No new members to add for {session_name}")
                    return 0
                
                # Setup progress bar
                with self.create_progress_bar(f"Adding members with {session_name}...", total) as progress_bar:
                    task = progress_bar.add_task("", total=total)
                    
                    for i, user in enumerate(all_participants[start_index:], start=start_index):
                        try:
                            if user.id in existing_ids:
                                progress_bar.advance(task)
                                continue
                            
                            # Add member
                            await client(InviteToChannelRequest(dest, [user]))
                            self.console.print(f"\n[green]✓ {session_name}: Added {user.username or user.id}")
                            count += 1
                            self.progress_manager.set_progress(session_name, i + 1)
                            
                            # Check daily limit
                            if count >= self.config_manager.config["limit_per_day"]:
                                self.console.print(f"[yellow]⚠️ Daily limit reached for {session_name}")
                                break
                            
                            await asyncio.sleep(self.config_manager.config["delay_between_adds"])
                            progress_bar.advance(task)
                            
                        except (errors.FloodWaitError, errors.UserPrivacyRestrictedError) as e:
                            self.console.print(f"\n[yellow]⚠️ {session_name}: {e}")
                            continue
                        except Exception as e:
                            self.console.print(f"\n[red]✗ {session_name}: Error - {e}")
                            continue
                
                return count
                
        except Exception as e:
            self.console.print(f"[red]⚠️ {session_name} failed: {e}")
            return 0
    
    def create_progress_bar(self, description, total):
        return Progress(
            TextColumn(f"[bold blue]{description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TimeRemainingColumn(),
            console=self.console,
            expand=False
        )
    
    async def send_messages(self, account, target_group, message, message_count):
        session_name = account["session_name"]
        try:
            async with TelegramClient(
                f"{SESSIONS_DIR}/{session_name}",
                account["api_id"],
                account["api_hash"]
            ) as client:
                entity = await client.get_entity(target_group)
                sent_count = 0
                
                with self.create_progress_bar(f"Sending messages with {session_name}...", message_count) as progress_bar:
                    task = progress_bar.add_task("", total=message_count)
                    
                    for i in range(message_count):
                        try:
                            await client.send_message(entity, message)
                            sent_count += 1
                            progress_bar.advance(task)
                            
                            if i < message_count - 1:
                                await asyncio.sleep(self.config_manager.config["message_delay"])
                                
                        except (errors.FloodWaitError, errors.ChatWriteForbiddenError) as e:
                            self.console.print(f"\n[yellow]⚠️ {session_name}: {e}")
                            break
                        except Exception as e:
                            self.console.print(f"\n[red]✗ Error sending message: {e}")
                            break
                
                # Update stats
                self.messaging_manager.update_account_stats(session_name, target_group, sent_count)
                return sent_count
                
        except Exception as e:
            self.console.print(f"[red]⚠️ {session_name} failed: {e}")
            return 0

class TelegramMemberAdder:
    def __init__(self):
        self.console = Console()
        self.ops = TelegramOperations(self.console)
        self.config_manager = self.ops.config_manager
        self.account_manager = self.ops.account_manager
        self.progress_manager = self.ops.progress_manager
        self.messaging_manager = self.ops.messaging_manager
        
    def display_banner(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        banner_panel = Panel(
            BANNER,
            title="[bold]TELEGRAM MEMBER ADDER[/bold]",
            subtitle="[italic]Advanced Account Management[/italic]",
            border_style="bold dark_orange",
            padding=(1, 4),
            expand=False
        )
        self.console.print(banner_panel)
        self.console.print("[white]                   Developed by [bold cyan]Tharuwa[/bold cyan]", style="dim")
        self.console.print("[bold dark_orange]──────────────────────────────────────────────────────────────\n")
    
    def add_account_menu(self):
        self.console.print("\n[bold green]➕ ADD NEW ACCOUNT[/]")
        api_id = input("API ID: ")
        api_hash = input("API HASH: ")
        session_name = input("Session name (e.g., phone number): ")
        
        if self.account_manager.add_account(api_id, api_hash, session_name):
            self.console.print(f"[green]✅ Account '{session_name}' added successfully!")
        else:
            self.console.print("[red]❌ Account with this session name already exists!")
    
    def remove_account_menu(self):
        accounts = self.account_manager.accounts
        if not accounts:
            self.console.print("[red]No accounts available to remove!")
            return
            
        self.console.print("\n[bold red]🗑️ REMOVE ACCOUNT[/]")
        self.console.print("[bold]Available accounts:[/]")
        for i, acc in enumerate(accounts, 1):
            self.console.print(f"{i}. {acc['session_name']}")

        try:
            selection = int(input("\nSelect account number to remove (0 to cancel): "))
            if selection == 0:
                return

            if 1 <= selection <= len(accounts):
                if self.account_manager.remove_account(selection-1):
                    self.console.print(f"[green]✅ Account removed successfully!")
                else:
                    self.console.print("[red]Failed to remove account!")
            else:
                self.console.print("[red]Invalid selection!")
        except ValueError:
            self.console.print("[red]Please enter a valid number!")
    
    async def run_daily_adding(self):
        self.config_manager.reset_daily_counters()
        accounts = self.account_manager.accounts
        
        if not accounts:
            self.console.print("[red]No accounts added! Add accounts first.")
            return 0
            
        # Display account sequence
        table = Table(title="\n[bold]ACCOUNT SEQUENCE[/]", box=box.ROUNDED)
        table.add_column("No.", style="cyan")
        table.add_column("Session", style="green")
        table.add_column("Progress", style="yellow")
        table.add_column("Status", style="magenta")
        
        for i, acc in enumerate(accounts, 1):
            progress = self.progress_manager.get_progress(acc["session_name"])
            status = "[green]Active" if progress > 0 else "[yellow]Pending"
            table.add_row(str(i), acc["session_name"], str(progress), status)
            
        self.console.print(table)
        
        # Process accounts sequentially
        total_added = 0
        for i, account in enumerate(accounts, 1):
            self.console.print(f"\n[bold green]🚀 STARTING ACCOUNT {i}/{len(accounts)}: {account['session_name']}[/]")
            added = await self.ops.add_members(account)
            total_added += added
            
            if added >= self.config_manager.config["limit_per_day"]:
                self.console.print(f"[yellow]⏹️ Account reached daily limit ({added}/{self.config_manager.config['limit_per_day']})")
            else:
                self.console.print(f"[green]✅ Account completed ({added} members added)")
                
        return total_added
    
    async def send_messages_menu(self):
        accounts = self.account_manager.accounts
        if not accounts:
            self.console.print("[red]No accounts available for messaging!")
            return
            
        self.console.print("\n[bold cyan]✉️ AUTO MESSAGE SENDER[/]")
        target_group = input("Enter target group/channel (with @): ")
        message = input("Enter message to send: ")
        
        # Get message count with limit
        max_messages = self.config_manager.config["message_limit"]
        try:
            message_count = int(input(f"How many times to send? (Max {max_messages}): ") or 1)
            message_count = max(1, min(message_count, max_messages))
        except ValueError:
            self.console.print("[red]Invalid number! Using default of 1")
            message_count = 1
            
        # Select account
        self.console.print("\n[bold]Available accounts:[/]")
        for i, acc in enumerate(accounts, 1):
            self.console.print(f"{i}. {acc['session_name']}")

        try:
            selection = int(input("\nSelect account to use: "))
            if 1 <= selection <= len(accounts):
                account = accounts[selection-1]
                sent = await self.ops.send_messages(account, target_group, message, message_count)
                self.console.print(f"\n[bold green]✅ Sent {sent}/{message_count} messages successfully!")
            else:
                self.console.print("[red]Invalid account selection!")
        except ValueError:
            self.console.print("[red]Please enter a valid number!")
    
    def show_progress_report(self):
        accounts = self.account_manager.accounts
        if not accounts:
            self.console.print("[red]No accounts available!")
            return
            
        table = Table(title="\n[bold]PROGRESS REPORT[/]", box=box.ROUNDED)
        table.add_column("Account", style="green")
        table.add_column("Member Progress", style="yellow")
        table.add_column("Messages Sent", style="magenta")
        table.add_column("Last Target", style="cyan")
        
        for account in accounts:
            session = account["session_name"]
            progress = self.progress_manager.get_progress(session)
            stats = self.messaging_manager.get_account_stats(session)
            table.add_row(
                session,
                str(progress),
                str(stats["sent"]),
                stats["last_target"]
            )
            
        self.console.print(table)
    
    def reset_progress_menu(self):
        self.console.print("\n[bold yellow]RESET PROGRESS OPTIONS[/]")
        self.console.print("1. Reset single account")
        self.console.print("2. Reset all accounts")
        self.console.print("3. Cancel")

        choice = input("Select option (1-3): ")

        if choice == "3":
            return

        accounts = self.account_manager.accounts
        if choice == "2":
            self.progress_manager.reset_all_progress()
            
            # Reset messaging counts
            for session in self.messaging_manager.stats:
                self.messaging_manager.stats[session]["sent"] = 0
            self.messaging_manager.save_stats()
            
            self.console.print("[green]✅ All progress reset successfully!")
        elif choice == "1":
            self.console.print("\n[bold]Available accounts:[/]")
            for i, acc in enumerate(accounts, 1):
                self.console.print(f"{i}. {acc['session_name']}")

            try:
                selection = int(input("Select account number to reset: "))
                if 1 <= selection <= len(accounts):
                    session_name = accounts[selection-1]["session_name"]
                    self.progress_manager.reset_account_progress(session_name)
                    self.messaging_manager.reset_account_stats(session_name)
                    self.console.print(f"[green]✅ Progress for '{session_name}' reset successfully!")
                else:
                    self.console.print("[red]Invalid selection!")
            except ValueError:
                self.console.print("[red]Please enter a valid number!")
    
    def main_menu(self):
        while True:
            self.console.print("\n[bold dark_orange]MAIN MENU[/]")
            self.console.print("1. Add Telegram Account")
            self.console.print("2. Remove Telegram Account")
            self.console.print("3. Start Daily Adding Process")
            self.console.print("4. Send Messages to Group/Channel")
            self.console.print("5. View Progress Report")
            self.console.print("6. Reset Progress")
            self.console.print("7. Exit")

            choice = input("Select option (1-7): ")

            if choice == "1":
                self.add_account_menu()
            elif choice == "2":
                self.remove_account_menu()
            elif choice == "3":
                total_added = asyncio.run(self.run_daily_adding())
                if total_added > 0:
                    self.console.print(f"\n[bold green]🏆 TOTAL MEMBERS ADDED TODAY: {total_added}[/]")
                else:
                    self.console.print("\n[bold yellow]⚠️ No members added this session")
            elif choice == "4":
                asyncio.run(self.send_messages_menu())
            elif choice == "5":
                self.show_progress_report()
            elif choice == "6":
                self.reset_progress_menu()
            elif choice == "7":
                self.console.print("[bold green]👋 Exiting... Thank you for using Member Adder!")
                break
            else:
                self.console.print("[red]Invalid selection! Please choose 1-7")

if __name__ == "__main__":
    # Initialize kill switch
    kill_switch = KillSwitchMonitor()
    kill_switch.start()
    
    # Create application instance
    app = TelegramMemberAdder()
    app.display_banner()
    
    # Ensure sessions directory exists
    if not os.path.exists(SESSIONS_DIR):
        os.mkdir(SESSIONS_DIR)
    
    # Start main application
    app.main_menu()