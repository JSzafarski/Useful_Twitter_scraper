import requests
import os
import json
from collections import deque
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
from datetime import date
import telebot

options = webdriver.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')  # Avoid detection
driver = webdriver.Chrome(options=options)

API_TOKEN = '' #use your own telegram api key
bot = telebot.TeleBot(API_TOKEN)

def time_converter(epoch_time):
    current_time = datetime.now()
    given_time = datetime.fromtimestamp(epoch_time)

    # Calculate the difference
    time_difference = current_time - given_time

    seconds = time_difference.total_seconds()

    if seconds < 60:
        return f"{int(seconds)} seconds ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{int(minutes)} minutes ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{int(hours)} hours ago"
    else:
        days = seconds // 86400
        return f"{int(days)} days ago"

def get_price(token, retries=3, delay=3):
    base_url = f"https://public-api.birdeye.so/defi/price?address={token}"
    headers = {
        "accept": "application/json",
        "x-chain": "solana",
        "X-API-KEY": "a6a4842f77d44a6c8a3d8e5757c64f10"
    }
    # i will ignore moon shot tokens
    for attempt in range(retries):
        try:
            response = requests.get(base_url, headers=headers)
            if response.status_code == 429:  # Too Many Requests
                print(f"Too many requests, retrying in {delay} seconds...")
                time.sleep(delay)  # Wait before retrying
                continue

            response.raise_for_status()  # Raise an error for other HTTP error codes
            return response.json()['data']['value']  # Return the token price
        except (requests.exceptions.RequestException,ValueError) as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == retries - 1:  # If it's the last attempt, raise the error
                return None
    return None

def convert_followers_count(followers_text):
    # Remove 'Followers' and strip extra spaces
    #returns 5 for 5000 but its doesnt amttter as its not enougth anyway
    followers_text = followers_text.replace("Followers", "").strip()

    # Match patterns like "1M", "1000", "101K", "91.5K"
    match = re.match(r'(\d+(\.\d+)?)([KMG]?)', followers_text)

    if match:
        number = float(match.group(1))  # Extract the number part as a float
        suffix = match.group(3).upper()  # Extract the suffix (K, M, G)

        # Apply conversion based on suffix
        if suffix == 'M':  # Millions
            return int(number * 1000000)
        elif suffix == 'K':  # Thousands
            return int(number * 1000)
        elif suffix == 'G':  # Billions (just in case)
            return int(number * 1000000000)
        else:
            return int(number)  # No suffix, return the number as is

    else:
        # If no match, return 0 or handle accordingly
        return 0

class ExpiringQueue:
    def __init__(self, expiration_time=300, storage_file="expired_tokens.json"):#raise to 15 min maybe later
        """
        Initializes the queue with a specified expiration time in seconds (default is 1 hour).
        Loads expired tokens from the storage file if it exists.
        """
        self.queue = deque()
        self.expiration_time = timedelta(seconds=expiration_time)
        self.storage_file = storage_file
        self.expired_items = self._load_expired_tokens()

    def _load_expired_tokens(self):
        """
        Loads expired tokens from the storage file if it exists.
        Returns a set of expired items.
        """
        if os.path.exists(self.storage_file):
            with open(self.storage_file, "r") as file:
                return set(json.load(file))
        return set()

    def _save_expired_tokens(self):
        """
        Saves the set of expired tokens to the storage file.
        """
        with open(self.storage_file, "w") as file:
            json.dump(list(self.expired_items), file)

    def _remove_expired(self):
        """
        Removes expired items from the queue.
        """
        now = datetime.now()
        while self.queue and (now - self.queue[0][1]) > self.expiration_time:
            expired_item = self.queue.popleft()  # Remove the oldest item
            print(f'removed {expired_item}')
            expired_address = expired_item[0].split(",", 1)[0]
            self.expired_items.add(expired_address)  # Mark only the address as expired
            self._save_expired_tokens()
            print(f"Expired & removed: {expired_item[0]}")

    def enqueue(self, item):
        """
        Adds an item to the queue with the current timestamp if:
        1. The item has not expired before.
        2. The item is not already in the queue.
        """
        self._remove_expired()
        address = item.split(",", 1)[0]  # Extract address before the first comma
        if address in self.expired_items:
            return False  # Prevent enqueue if address has expired before
        if any(queue_item[0].split(",", 1)[0] == address for queue_item in self.queue):
            return False  # Prevent enqueue if address is already in queue

        #self.queue.append((item, datetime.now()))
        self.queue.insert(0, (item, datetime.now())) # make sure newest unseen tokens are checked as priority
        # Print the current queue after enqueueing
        print("Current Queue:", self.to_list())
        #print(f"'{item}' enqueued successfully.")
        return True

    def dequeue(self):
        """
        Removes and returns the oldest non-expired item in the queue.
        If the queue is empty or all items are expired, returns None.
        """
        self._remove_expired()
        if self.queue:
            item = self.queue.popleft()[0]
            expired_address = item.split(",", 1)[0]
            self.expired_items.add(expired_address)  # Store only address as expired
            self._save_expired_tokens()
            return item
        return None

    def peek(self):
        """
        Returns the oldest non-expired item without removing it.
        If the queue is empty or all items are expired, returns None.
        """
        self._remove_expired()
        if self.queue:
            return self.queue[0][0]
        return None

    def size(self):
        """
        Returns the number of non-expired items in the queue.
        """
        self._remove_expired()
        return len(self.queue)

    def to_list(self):
        """
        Returns the queue as a list of strings, excluding expired items.
        """
        self._remove_expired()
        return [item[0] for item in self.queue]
    def refresh_queue(self):
        """
            Refresh the current queue (since the operation is not asynchronous!)
        """
        self._remove_expired()

# Define URL
url = "https://gmgn.ai/defi/quotation/v1/rank/sol/swaps/1h"

# Query Parameters
params = {
    "device_id": "b50170c1-79f6-452e-83c1-a25f2e6e948a",
    "client_id": "gmgn_web_2025.0211.185728",
    "from_app": "gmgn",
    "app_ver": "2025.0211.185728",
    "tz_name": "Europe/London",
    "tz_offset": "0",
    "app_lang": "en",
    "orderby": "change1m",
    "direction": "desc",
    "filters[]": "renounced",
    "min_marketcap": "100000",
    "max_created": "1h"
}

# Headers
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "referer": "https://gmgn.ai/?chain=sol",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"132.0.6834.160"',
    "sec-ch-ua-full-version-list": '"Not A(Brand";v="8.0.0.0", "Chromium";v="132.0.6834.160", "Google Chrome";v="132.0.6834.160"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "if-none-match": 'W/"34d7-Kq2UgqOpIHRnbLwmOwkPMmriX8E"',
    "priority": "u=1, i"
}

# Cookies
cookies = {
    "_ga": "GA1.1.1659988064.1735842424",
    "__cf_bm": "2IObLfzQUZ8N1xs4IC.71Pzya.Z_AZSvFTE2SPep3_8-1739316330-1.0.1.1-pGJ.076opElkCo3Fwlj6_wrIyCysJAtUvw3oIGb_iNKr22gCYnIzo_OqfZfDXAX4_6QdQMGt06S98.TKB8OXrw",
    "cf_clearance": ".rE2q2UdjBFlaVIlL9B7mdgU8yLQTspJSYZARaKQJm0-1739316331-1.2.1.1-jRl6MhSZK8sdD0KYRa2TfT9duSVhpCd3e.nBx1RF5j7MLvy7Y6E4XslM_dOvFrPrWPxdcO2L8EviEEv6dZQfGjetqWQYCP9vWrO7wEIcinLqc4erH0ezNNGU5mjfq04Uvq5AF6QXIeYVv1egmc5busLMhuu8R1Gz8z31.Lhn7.pTtg9JwPdBzRCrl8E_ERHfFY6INPNVkEtf9ghoYGGDkUMeSbZtys51udZxcm8WTQ9BGOl7gbNMo2BnlIDxLD0scnrPG.y29MQxxuahoTt.MKujLmm4uy3JJ416ppA2oD_A.gs9OUlH3R46t.Zq6YkjVHIQqQ5FKXqtHgpQdu.73w",
    "_ga_0XM0LYXGC8": "GS1.1.1739316329.106.0.1739316335.0.0.0"
}


# TODO USE SESSION HANDLING SO THIS DOESN'T NEED TO BE HARDCODED EACH TIME I RESTART THE MACHINE
def post_content_verification(target_text, *search_strings):
    #verify that the post actually is relevant to the token of interest to avoid confussion as yesterday some top post was not related tot he quesry
    """
       Checks if at least one of the given search strings appears in the target text.

       :param target_text: The multiline string to search within.
       :param search_strings: The strings to search for.
       :return: True if at least one of the search strings is found, otherwise False.
    """
    return any(s in target_text for s in search_strings)
small_account_blacklist_file = 'blacklist.txt'
pinged_tokens_file = "pinged.txt"
#if the mc drops sub 100k then ignore the token even if its sill not expired yet.
def main(): #change to check it once but only if its over 1h old
    print('starting.....')
    token_queue = ExpiringQueue(expiration_time=30) # for testing
    small_account_blacklist = []
    pinged_tokens = []  # avoid re-ping
    # Load the usernames back into a list
    with open(small_account_blacklist_file, "r") as file:
        small_account_blacklist = [line.strip() for line in file]  # Strip removes trailing newlines
    with open(pinged_tokens_file, "r") as file:
        pinged_tokens = [line.strip() for line in file]  # Strip removes trailing newlines
    username = "" # YOUR USERNAME (needs to move to an .env file)
    password = "" # YOU PASSWORD
    #TODO possibly use multiple accounts if one runs out of daily limit or use twitter premium?
    # Login to Twitter
    driver.get("https://twitter.com/login")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "text"))
    )
    # Enter username and proceed
    username_field = driver.find_element(By.NAME, "text")
    username_field.send_keys(username)
    username_field.send_keys(Keys.RETURN)
    # Wait for password field
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "password"))
    )
    password_field = driver.find_element(By.NAME, "password")
    password_field.send_keys(password)
    password_field.send_keys(Keys.RETURN)
    # Wait for the home page
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//a[@aria-label='Profile']"))
    )
    print("Login successful!")
    while True:
        try:
            print('Checking for new trending Tokens...')
            response = requests.get(url, params=params, headers=headers,cookies=cookies)
            response.raise_for_status()
            tokens_data = response.json()['data']['rank']

            def ends_with_moon(s: str) -> bool:
                return s.endswith("moon")


            for token in tokens_data:
                print(token)
                if int(token['market_cap']) >= 10000000 or ends_with_moon(token['address']): #remove scam shit or just too late
                    #ignore moonshot tokens for now
                    if token['address'] not in pinged_tokens:
                        print(f'removed due to high mc (rug) : {token['symbol']}')
                        pinged_tokens.append(token['address'])  # assume its invalid to be pinged
                else:
                    if token['address'] not in pinged_tokens:
                        token_queue.enqueue(f"{token['address']},{token['symbol']},{token['open_timestamp']}")
            currently_watched_tokens = token_queue.to_list()
            print(f"current tokens in queue: {len(currently_watched_tokens)}")
            print(f"removed tokens: {len(pinged_tokens)}")
            for token in currently_watched_tokens:
                start_time = time.time()
                address, symbol,time_created = token.split(',')
                if address in pinged_tokens:
                    continue
                else:
                    token_price = get_price(address)
                    if token_price is not None:
                        if token_price * 1000000000 <= 100000: #this won't work if the supply is burned or different than 1bn
                            # under the passing threshold
                            pinged_tokens.append(address) #assume its invalid to be pinged
                            with open(pinged_tokens_file, "a") as file:
                                file.write(address + "\n")  # Add a newline character to separate entries
                            continue
                if "$" not in symbol:
                    symbol_variation = "$"+symbol
                else:
                    symbol_variation = symbol.replace('$', '')
                print(f'Checking token: {symbol}')
                today = str(date.today().strftime("%Y-%m-%d"))
                query = f"{address}%20{symbol}%20{symbol_variation}%20{symbol.capitalize()}%20{symbol_variation.capitalize()}"
                twitter_search_query = f"https://x.com/search?q={query}%20since%3A{today}&src=typed_query"
                driver.get(twitter_search_query)
                # Wait for tweets to load
                try:
                    WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.TAG_NAME, "article"))
                    )
                    # Parse the page source with BeautifulSoup
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    tweets = soup.find_all('article')
                except Exception as e:
                    print('error reading posts or no posts found.')
                    time.sleep(10)
                    continue
                username_regex = r"@(\w+)"
                # Extract and print the top 5 tweets
                for j, tweet in enumerate(tweets[:4]):
                    # so sometimes an unrelated post to the query can appear with unrelated token mitigate this by verifying their content contains the token of interest
                    tweet_text = tweet.get_text(separator=" ").strip()
                    check = post_content_verification(tweet_text,address ,symbol ,symbol_variation ,symbol.capitalize() ,symbol_variation.capitalize())
                    if check: # contains relevant content
                        username_match = re.search(username_regex, tweet_text)
                        username = username_match.group(0) if username_match else "No username found"
                        if username in small_account_blacklist:
                            print('skipping user: ',username)
                            continue #same time
                        driver.get(f"https://x.com/{username}")
                        # Wait for the followers count element to load
                        followers_xpath = ("//*[@id='react-root']/div/div/div[2]/main/div/"
                                           "div/div/div/div/div[3]/div/div/div[1]/div/div[5]/div[2]/a")
                        try:
                            followers_element = WebDriverWait(driver, 6).until(
                                EC.presence_of_element_located((By.XPATH, followers_xpath))
                            )
                            followers_count = followers_element.text
                            follower_count_integer = convert_followers_count(followers_count)

                            def precede_fullstop_with_backslash(text):
                                markdown_v2_chars = r"_*~>#+-=|{}.!"
                                for char in markdown_v2_chars:
                                    text = text.replace(char, f'\\{char}')  # Double backslash to properly escape
                                return text

                            if follower_count_integer>=150000:
                                print(f'🔥 big account posted !: {username} {followers_count} {address} ')
                                group_id = -1002461223139
                                admin_id = 7321612298
                                bot.send_message(group_id, precede_fullstop_with_backslash(f'🔥 Big account posted!: {username}'
                                f'  {followers_count}\n\n📖 Ca: `{address}`\n\n📈 [gmgn](https://gmgn.ai/sol/token/{address})\n\n📎 [Query Link]({twitter_search_query})\n\n'
                                                             f'🕙 made: {time_converter(int(time_created))}\n\nℹ️ Disclaimer: manually inspect the token before deciding to buy!'),disable_web_page_preview=True,parse_mode="MarkdownV2") # there might be an error here
                                pinged_tokens.append(address) #remove the token from the queue
                                with open(pinged_tokens_file, "a") as file:
                                    file.write(address + "\n")  # Add a newline character to separate entries
                            else:
                                with open(small_account_blacklist_file, "a") as file:
                                    file.write(username + "\n")  # Add a newline character to separate entries
                                small_account_blacklist.append(username)
                                print(f'Blacklisted a small account: {username}')
                                #add the user to a blacklist ot not check them again ( saves time and resources)
                        except Exception as e:
                            print(e)
                            time.sleep(2)
                            pass
                        time.sleep(5)
                end_time = time.time()
                execution_time = end_time - start_time
                print(f"Execution time: {execution_time:.6f} seconds")
                time.sleep(12)
        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")
        time.sleep(20)#moderate delay to prevent twitter throttle.


main()

#exponential backoff if not loading
#TODO add a purchase option for fast buy and set a 100 TP
# TWEAK DELAYS POSSIBLY DO PREMIUM FOR LESS RESTRICTION