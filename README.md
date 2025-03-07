## Overview
This script automates cryptocurrency price monitoring, Twitter sentiment analysis, and Telegram notifications for trending tokens. It:

- Scrapes trending Solana tokens from GMGN.ai
- Checks their presence on Twitter
- Extracts engagement data from tweets
- Notifies via Telegram when large accounts mention a token
- Implements a queue to track monitored tokens
- Logs activities and errors for debugging

## Features
- **Web Scraping**: Uses Selenium and BeautifulSoup to analyze Twitter activity.
- **API Integration**: Fetches token price data from Birdeye's public API.
- **Queue System**: Tracks tokens for a limited time to avoid duplicate checks.
- **Blacklist Handling**: Filters out small accounts for efficiency.
- **Telegram Alerts**: Sends notifications for significant activity.
- **Logging Mechanism**: Saves logs for debugging and monitoring.

## Requirements
Ensure you have the following installed:

- Python 3.x
- Selenium
- BeautifulSoup4
- Requests
- Telebot (pyTelegramBotAPI)
- Logging (built-in module)

## Installation
```sh
pip install selenium beautifulsoup4 requests telebot
```

You will also need:
- Google Chrome and the Chrome WebDriver
- A Telegram bot API key
- A Twitter account for login

## Configuration
1. Update `API_TOKEN` with your Telegram bot key.
2. Modify `username` and `password` with your Twitter credentials.
3. If needed, adjust `headers` and `params` for GMGN.ai requests.
4. Set the logging level in `logging.basicConfig()` as required.

## Usage
Run the script using:
```sh
python script.py
```
The bot will:
- Log in to Twitter
- Continuously monitor token trends
- Extract Twitter mentions
- Alert on major mentions via Telegram
- Log activities and errors for analysis

## Notes
- The script includes built-in rate limiting and retries.
- Ensure Twitter login details are correct to avoid authentication failures.
- Modify time intervals (`time.sleep()`) to optimize performance and avoid throttling.
- Logs will be stored in `logfile.log` for debugging.

## Future Improvements
- Implement session handling to avoid re-logging into Twitter.
- Use multiple Twitter accounts to bypass API limits.
- Improve token validation to filter out scams more effectively.
- Enhance logging with more granular event tracking.

## Disclaimer
This tool is for educational purposes only. Use at your own risk.

