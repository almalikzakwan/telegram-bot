# 🤖 HR Management Telegram Bot

A Telegram bot built with Python for managing HR requests — including Medical Certificate (MC) submissions and leave applications — directly through the Telegram interface.

---

## ✨ Features

- **User Registration** — First-time users complete a one-time profile setup (full name, employee ID, department).
- **Apply MC** — Submit a Medical Certificate with photo proof. Photo is saved to `storage/mc/`.
- **Apply Leave** — Choose from 5 leave types and enter date(s). Balance is validated and deducted automatically.
- **My Balance** — View remaining entitlement for all leave types at a glance.
- **My History** — View the last 5 submitted requests.
- **Back Navigation** — Every input step has a `⬅️ Back` button to return without submitting.
- **Auto-restart** — After each submission, a thank-you message is shown and the main menu restarts.

### 🌴 Leave Types & Default Entitlements

| Leave Type        | Default Days |
|-------------------|:------------:|
| 📅 Annual Leave   | 14           |
| 🚨 Emergency Leave | 3           |
| 💸 Unpaid Leave   | Unlimited    |
| 👶 Paternity Leave | 7           |
| 🤱 Maternity Leave | 60          |
| 🤒 Medical Leave (MC) | 14      |

---

## 🗂️ Project Structure

```
telegram-bot/
├── main.py                   # Entry point — app setup & ConversationHandler wiring
├── classes/
│   ├── __init__.py           # Package re-exports
│   ├── states.py             # Conversation state constants & LEAVE_TYPES config
│   ├── database.py           # SQLite layer (users, leave_balance, leave_requests)
│   ├── keyboards.py          # Inline keyboard builders
│   ├── storage.py            # MC photo file I/O helpers
│   ├── reg_handlers.py       # Registration flow handlers
│   └── hr_handlers.py        # HR operation handlers (leave, MC, balance, history)
├── storage/
│   ├── hr_bot.db             # SQLite database (auto-created on first run)
│   ├── app.log               # Application activity log
│   └── mc/                   # Uploaded MC photo files
├── .env                      # Bot token (not committed to version control)
├── requirements.txt
└── README.md
```

---

## 🛠️ Tools & Dependencies

- **Python** 3.11+
- **[python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)** 22.7
- **python-dotenv** 1.2.2
- **SQLite3** (built-in, no extra install required)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd telegram-bot
```

### 2. Create a virtual environment (recommended)

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your bot token

Create a `.env` file in the project root:

```env
token = "your-telegram-bot-token-here"
```

> Get your token from [@BotFather](https://t.me/BotFather) on Telegram.

### 5. Run the bot

```bash
# Linux / macOS
python3 main.py

# Windows
python main.py
```

The `storage/` directory and SQLite database are created automatically on first run.

---

## 💬 Bot Commands

| Command    | Description                        |
|------------|------------------------------------|
| `/start`   | Start the bot / return to main menu |
| `/cancel`  | Cancel the current operation        |

---

## 🔄 Conversation Flow

```
/start
  ├── [New user]      → Name → Employee ID → Department → ✅ Profile created
  └── [Returning user]──────────────────────────────────────────────────────┐
                                                                            ▼
                                    ┌──────────────────────────────────────────┐
                                    │  🤒 Apply MC   │  🌴 Apply Leave         │
                                    │  📊 My Balance │  📋 My History          │
                                    └──────────────────────────────────────────┘
                                           │                    │
                          ┌────────────────┘                    └────────────────────┐
                          ▼                                                          ▼
                 Upload photo [⬅️ Back]                    Select leave type [⬅️ Back]
                 Saved to storage/mc/                      Enter dates [⬅️ Back]
                 MC balance −1 day                         Balance checked & deducted
                          └──────────────────┬──────────────────────────────────────┘
                                             ▼
                                  ✅ Thank you! + menu restarts
```

---

## 🗄️ Database Schema

| Table             | Description                                       |
|-------------------|---------------------------------------------------|
| `users`           | Employee profile (name, employee ID, department)  |
| `leave_balance`   | Per-user, per-type balance (total / used days)    |
| `leave_requests`  | All submitted leave/MC requests with status       |

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).