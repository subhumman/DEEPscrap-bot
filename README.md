# Telegram Bot Project

This is a Telegram bot project that includes a parser and database functionality.

## Project Structure

```
├── .env                    # Environment variables (not tracked by git)
├── .gitignore             # Git ignore file
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── bot.py                # Main bot file
├── config.py             # Configuration settings
├── database.py           # Database operations
├── handlers.py           # Bot command handlers
├── keyboards.py          # Telegram keyboard layouts
└── parser.py             # Web scraping functionality
```

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with the following variables:
   ```
   BOT_TOKEN=your_bot_token
   MANAGER_CHANNEL_ID=your_channel_id
   BASE_URL=https://krasnodar.23met.ru
   PROXIES=proxy1,proxy2  # Optional
   ```

## Running the Bot

```bash
python bot.py
```

## Features

- Telegram bot with command handling
- Web scraping functionality
- Database integration
- Proxy support
- Logging system

## Security Notes

- Never commit the `.env` file
- Keep your bot token secure
- Use environment variables for sensitive data 