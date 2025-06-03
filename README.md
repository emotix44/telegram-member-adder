# Telegram Member Adder

A powerful, fully featured Telegram member adder script built for Termux.  
Supports multiple accounts, session management, daily limits, rich UI, and progress tracking.

> ⚙️ Developed with [Telethon](https://github.com/LonamiWebs/Telethon) and `rich` for enhanced visuals.

---

## 🚀 Features

- ✅ Add members from one group to another
- ✅ Multi-account support with session files
- ✅ Daily limit enforcement per account
- ✅ Auto resume from last added member (per session)
- ✅ JSON-based configuration and progress tracking
- ✅ Rich UI with animated progress bars and clean output
- ✅ Colorful banner and terminal-friendly design
- ✅ Termux and Android friendly

---

## 📦 Requirements

- Termux (Android)
- Python 3
- `telethon`, `rich` libraries

---

## 🔧 Installation

```bash
pkg update && pkg upgrade
pkg install python git
pip install telethon rich
git clone https://github.com/emotix44/telegram-member-adder
cd telegram-member-adder
python TelegramAutoAdder.py

🛠 First-Time Setup

1. On first run, it will ask:

source_group: Group to copy members from

dest_group: Group to add members to

limit_per_day: Max members to add per account each day



2. Save your accounts in accounts.json in this format:



[
  {
    "api_id": 123456,
    "api_hash": "your_api_hash",
    "session_name": "account1"
  },
  {
    "api_id": 654321,
    "api_hash": "another_api_hash",
    "session_name": "account2"
  }
]

3. When run, it will create a sessions/ folder and login for each account.




---

📁 Files and What They Do

File	Purpose

TelegramAutoAdder.py	Main script
accounts.json	Store your multiple account configs
config.json	Group source/target + limits
progress.json	Tracks where each session left off
messaging.json	Reserved for messaging stats
sessions/	Stores Telegram session files



---

❗ Notes

This script is for educational purposes only.

Do not abuse Telegram's ToS — use responsibly and legally.

Some accounts may face temporary restrictions if overused.



---

👨‍💻 Author

Tharuwa
🌐 GitHub: emotix44


