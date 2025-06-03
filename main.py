import requests

def check_remote_status():
    try:
        response = requests.get(
            "https://raw.githubusercontent.com/emotix44/telegram-member-adder/main/status.txt"
        )
        if response.text.strip().upper() != "ON":
            print("❌ Script has been disabled by the owner.")
            exit()
    except:
        print("⚠️ Could not verify script status. Continuing anyway...")

check_remote_status()

import asyncio
import json
import os
import datetime
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import ChannelParticipantsRecent
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich import box

console = Console()
os.system('clear' if os.name == 'posix' else 'cls')

# Enhanced ASCII Banner
banner = """
[bold dark_orange]
 ███╗   ███╗███████╗███╗   ███╗██████╗ ███████╗██████╗     █████╗ ██████╗ ██████╗ ███████╗██████╗
 ████╗ ████║██╔════╝████╗ ████║██╔══██╗██╔════╝██╔══██╗   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗
 ██╔████╔██║█████╗  ██╔████╔██║██████╔╝█████╗  ██████╔╝   ███████║██║  ██║██║  ██║█████╗  ██████╔╝
 ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██╔══██╗██╔══╝  ██╔══██╗   ██╔══██║██║  ██║██║  ██║██╔══╝  ██╔══██╗
 ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║██║  ██║███████╗██║  ██║██╗██║  ██║██████╔╝██████╔╝███████╗██║  ██║
 ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
[/bold dark_orange]
"""

# Create a styled panel for the banner
banner_panel = Panel(
    banner,
    title="[bold]TELEGRAM MEMBER ADDER[/bold]",
    subtitle="[italic]Advanced Account Management[/italic]",
    border_style="bold dark_orange",
    padding=(1, 4),
    expand=False
)

console.print(banner_panel)
console.print("[white]                   Developed by [bold cyan]Tharuwa[/bold cyan]", style="dim")
console.print("[bold dark_orange]──────────────────────────────────────────────────────────────\n")

# Load config
if not os.path.exists("config.json"):
    config = {
        "source_group": input("Enter source group username (with @): "),
        "dest_group": input("Enter destination group username (with @): "),
        "limit_per_day": int(input("Daily member limit per account: ")),
        "delay_between_adds": 10,
        "last_run_date": None,
        "message_delay": 5,
        "message_limit": 20
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)
else:
    with open("config.json") as f:
        config = json.load(f)

SOURCE_GROUP = config["source_group"]
DEST_GROUP = config["dest_group"]
LIMIT_PER_DAY = config["limit_per_day"]
DELAY = config.get("delay_between_adds", 10)
MESSAGE_DELAY = config.get("message_delay", 5)
MESSAGE_LIMIT = config.get("message_limit", 20)

# Load or create accounts file
if not os.path.exists("accounts.json"):
    with open("accounts.json", "w") as f:
        json.dump([], f)

# Load progress
if os.path.exists("progress.json"):
    with open("progress.json") as f:
        progress = json.load(f)
else:
    progress = {}

# Load messaging stats
if os.path.exists("messaging.json"):
    with open("messaging.json") as f:
        messaging_stats = json.load(f)
else:
    messaging_stats = {}

# Session folder
if not os.path.exists("sessions"):
    os.mkdir("sessions")

def save_accounts(accounts):
    with open("accounts.json", "w") as f:
        json.dump(accounts, f, indent=2)

def load_accounts():
    with open("accounts.json") as f:
        return json.load(f)

def save_progress():
    with open("progress.json", "w") as f:
        json.dump(progress, f)

def save_config():
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

def save_messaging_stats():
    with open("messaging.json", "w") as f:
        json.dump(messaging_stats, f)

async def add_members(api_id, api_hash, session_name):
    try:
        async with TelegramClient(f"sessions/{session_name}", api_id, api_hash) as client:
            source = await client.get_entity(SOURCE_GROUP)
            dest = await client.get_entity(DEST_GROUP)

            existing_members = await client.get_participants(dest)
            existing_ids = {u.id for u in existing_members}

            all_participants = await client.get_participants(source, filter=ChannelParticipantsRecent())
            start_index = progress.get(session_name, 0)
            count = 0

            # Progress tracking setup
            total = len(all_participants) - start_index
            if total <= 0:
                console.print(f"[yellow]No new members to add for {session_name}")
                return 0

            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=None),
                "[progress.percentage]{task.percentage:>3.0f}%",
                "•",
                TimeRemainingColumn()
            ) as progress_bar:
                task = progress_bar.add_task(f"[cyan]Adding members with {session_name}...", total=total)

                for i, user in enumerate(all_participants[start_index:], start=start_index):
                    try:
                        if user.id in existing_ids:
                            progress_bar.advance(task)
                            continue

                        await client(InviteToChannelRequest(dest, [user]))
                        console.print(f"\n[green]✓ [bold]{session_name}:[/] Added {user.username or user.id}")
                        count += 1
                        progress[session_name] = i + 1
                        save_progress()

                        if count >= LIMIT_PER_DAY:
                            console.print(f"[yellow]⚠️ Daily limit reached for {session_name}")
                            break

                        await asyncio.sleep(DELAY)
                        progress_bar.advance(task)

                    except KeyboardInterrupt:
                        console.print("\n[yellow]⏹️ Operation interrupted by user")
                        progress[session_name] = i
                        save_progress()
                        return count

                    except Exception as e:
                        console.print(f"\n[red]✗ [bold]{session_name}:[/] Error adding user - {e}")
                        continue

            return count

    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Operation canceled by user")
        return 0
    except Exception as e:
        console.print(f"[red]⚠️ {session_name} login failed: {e}")
        return 0

async def run_accounts_sequentially():
    accounts = load_accounts()
    if not accounts:
        console.print("[red]No accounts added! Use option 1 to add accounts first.")
        return False

    # Display account summary
    table = Table(title="\n[bold]ACCOUNT SEQUENCE[/]", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("No.", style="cyan", width=5)
    table.add_column("Session Name", style="green")
    table.add_column("API ID", style="yellow")
    table.add_column("Progress", style="blue")

    for i, acc in enumerate(accounts, 1):
        progress_val = progress.get(acc["session_name"], 0)
        table.add_row(str(i), acc["session_name"], str(acc["api_id"]), str(progress_val))
    
    console.print(table)
    
    # Run accounts sequentially
    total_added = 0
    for i, acc in enumerate(accounts, 1):
        console.print(f"\n[bold green]🚀 STARTING ACCOUNT {i}/{len(accounts)}: {acc['session_name']}[/]")
        added = await add_members(acc["api_id"], acc["api_hash"], acc["session_name"])
        total_added += added
        
        if added >= LIMIT_PER_DAY:
            console.print(f"[yellow]⏹️ Account {acc['session_name']} reached daily limit ({added}/{LIMIT_PER_DAY})")
        else:
            console.print(f"[green]✅ Account {acc['session_name']} completed ({added} members added)")
    
    return total_added

def add_account():
    accounts = load_accounts()
    console.print("\n[bold green]➕ ADD NEW ACCOUNT[/]")
    
    api_id = input("API ID: ")
    api_hash = input("API HASH: ")
    session_name = input("Session name (e.g., phone number): ")
    
    # Check if session name already exists
    if any(acc["session_name"] == session_name for acc in accounts):
        console.print("[red]❌ Account with this session name already exists!")
        return
    
    accounts.append({
        "api_id": api_id,
        "api_hash": api_hash,
        "session_name": session_name
    })
    
    save_accounts(accounts)
    console.print(f"[green]✅ Account '{session_name}' added successfully!")

def remove_account():
    accounts = load_accounts()
    if not accounts:
        console.print("[red]No accounts available to remove!")
        return
    
    console.print("\n[bold red]🗑️ REMOVE ACCOUNT[/]")
    console.print("[bold]Available accounts:[/]")
    for i, acc in enumerate(accounts, 1):
        console.print(f"{i}. {acc['session_name']}")
    
    try:
        selection = int(input("\nSelect account number to remove (0 to cancel): "))
        if selection == 0:
            return
            
        if 1 <= selection <= len(accounts):
            removed_acc = accounts.pop(selection-1)
            session_name = removed_acc["session_name"]
            
            # Remove from progress tracking
            if session_name in progress:
                del progress[session_name]
                save_progress()
            
            # Remove from messaging stats
            if session_name in messaging_stats:
                del messaging_stats[session_name]
                save_messaging_stats()
            
            # Remove session file if exists
            session_file = f"sessions/{session_name}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            
            save_accounts(accounts)
            console.print(f"[green]✅ Account '{session_name}' removed successfully!")
        else:
            console.print("[red]Invalid selection!")
    except ValueError:
        console.print("[red]Please enter a valid number!")

def show_progress():
    accounts = load_accounts()
    if not accounts:
        console.print("[red]No accounts available!")
        return
    
    table = Table(title="\n[bold]PROGRESS REPORT[/]", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Account", style="green")
    table.add_column("Member Progress", style="yellow")
    table.add_column("Messages Sent", style="magenta")
    table.add_column("Status", style="blue")
    
    for acc in accounts:
        session = acc["session_name"]
        member_progress = progress.get(session, 0)
        msg_count = messaging_stats.get(session, {}).get("sent", 0)
        status = "[green]Active" if member_progress > 0 or msg_count > 0 else "[yellow]Pending"
        table.add_row(session, str(member_progress), str(msg_count), status)
    
    console.print(table)

def reset_progress():
    console.print("\n[bold yellow]RESET PROGRESS OPTIONS[/]")
    console.print("1. Reset single account")
    console.print("2. Reset all accounts")
    console.print("3. Cancel")
    
    choice = input("Select option (1-3): ")
    
    if choice == "3":
        return
    
    accounts = load_accounts()
    if choice == "2":
        for acc in accounts:
            progress[acc["session_name"]] = 0
        save_progress()
        console.print("[green]✅ All progress reset successfully!")
    elif choice == "1":
        console.print("\n[bold]Available accounts:[/]")
        for i, acc in enumerate(accounts, 1):
            console.print(f"{i}. {acc['session_name']}")
        
        try:
            selection = int(input("Select account number to reset: "))
            if 1 <= selection <= len(accounts):
                session_name = accounts[selection-1]["session_name"]
                progress[session_name] = 0
                save_progress()
                console.print(f"[green]✅ Progress for '{session_name}' reset successfully!")
            else:
                console.print("[red]Invalid selection!")
        except ValueError:
            console.print("[red]Please enter a valid number!")

def check_daily_limit_reset():
    today = datetime.date.today().isoformat()
    reset_done = False
    
    if config.get("last_run_date") != today:
        # Reset all progress if it's a new day
        accounts = load_accounts()
        for acc in accounts:
            progress[acc["session_name"]] = 0
            
            # Reset messaging stats for this account
            if acc["session_name"] in messaging_stats:
                messaging_stats[acc["session_name"]]["sent"] = 0
                save_messaging_stats()
        
        save_progress()
        config["last_run_date"] = today
        save_config()
        console.print("[green]♻️ New day detected - counters reset")
        reset_done = True
    
    return reset_done

async def send_messages():
    accounts = load_accounts()
    if not accounts:
        console.print("[red]No accounts available for messaging!")
        return
    
    console.print("\n[bold cyan]✉️ AUTO MESSAGE SENDER[/]")
    target_group = input("Enter target group/channel (with @): ")
    message = input("Enter message to send: ")
    message_count = int(input(f"How many times to send? (Max {MESSAGE_LIMIT}): ") or 1)
    
    # Validate message count
    message_count = min(max(1, message_count), MESSAGE_LIMIT)
    
    console.print("\n[bold]Available accounts:[/]")
    for i, acc in enumerate(accounts, 1):
        console.print(f"{i}. {acc['session_name']}")
    
    try:
        selection = int(input("\nSelect account to use: "))
        if 1 <= selection <= len(accounts):
            account = accounts[selection-1]
            api_id = account["api_id"]
            api_hash = account["api_hash"]
            session_name = account["session_name"]
            
            # Initialize messaging stats for account
            if session_name not in messaging_stats:
                messaging_stats[session_name] = {"sent": 0, "last_target": ""}
            
            console.print(f"\n[bold green]✉️ STARTING MESSAGING WITH {session_name}[/]")
            console.print(f"[cyan]Target:[/] {target_group}")
            console.print(f"[cyan]Message:[/] {message}")
            console.print(f"[cyan]Count:[/] {message_count}")
            
            try:
                async with TelegramClient(f"sessions/{session_name}", api_id, api_hash) as client:
                    entity = await client.get_entity(target_group)
                    
                    # Progress bar setup
                    with Progress(
                        TextColumn("[bold blue]{task.description}"),
                        BarColumn(bar_width=None),
                        "[progress.percentage]{task.percentage:>3.0f}%",
                        "•",
                        TimeRemainingColumn()
                    ) as progress_bar:
                        task = progress_bar.add_task("[cyan]Sending messages...", total=message_count)
                        
                        for i in range(message_count):
                            try:
                                await client.send_message(entity, message)
                                sent_count = i + 1
                                console.print(f"\n[green]✓ Sent message {sent_count}/{message_count}")
                                
                                # Update messaging stats
                                messaging_stats[session_name]["sent"] += 1
                                messaging_stats[session_name]["last_target"] = target_group
                                save_messaging_stats()
                                
                                progress_bar.advance(task)
                                
                                # Skip delay for last message
                                if i < message_count - 1:
                                    await asyncio.sleep(MESSAGE_DELAY)
                                    
                            except Exception as e:
                                console.print(f"\n[red]✗ Error sending message: {e}")
                                break
                    
                    console.print(f"\n[bold green]✅ Messaging completed! Sent {sent_count} messages")
                    return True
                    
            except Exception as e:
                console.print(f"[red]⚠️ Error connecting with {session_name}: {e}")
                return False
        else:
            console.print("[red]Invalid account selection!")
            return False
    except ValueError:
        console.print("[red]Please enter a valid number!")
        return False

def main_menu():
    while True:
        console.print("\n[bold dark_orange]MAIN MENU[/]")
        console.print("1. Add Telegram Account")
        console.print("2. Remove Telegram Account")
        console.print("3. Start Daily Adding Process")
        console.print("4. Send Messages to Group/Channel")
        console.print("5. View Progress Report")
        console.print("6. Reset Progress")
        console.print("7. Exit")
        
        choice = input("Select option (1-7): ")
        
        if choice == "1":
            add_account()
        elif choice == "2":
            remove_account()
        elif choice == "3":
            check_daily_limit_reset()
            total_added = asyncio.run(run_accounts_sequentially())
            
            if total_added > 0:
                console.print(f"\n[bold green]🏆 MISSION COMPLETED![/]")
                console.print(f"[bold cyan]Total members added today: {total_added}")
                console.print("[yellow]⏳ Next run available tomorrow")
            else:
                console.print("\n[bold yellow]⚠️ No members added this session")
        elif choice == "4":
            asyncio.run(send_messages())
        elif choice == "5":
            show_progress()
        elif choice == "6":
            reset_progress()
        elif choice == "7":
            console.print("[bold green]👋 Exiting... Thank you for using Member Adder!")
            break
        else:
            console.print("[red]Invalid selection! Please choose 1-7")

if __name__ == "__main__":
    main_menu()
