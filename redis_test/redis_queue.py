import os
import asyncio
import aiohttp
import sqlite3
import redis.asyncio as redis
import requests

# 1. asyncio + queue (single-threaded: queue could be redis or in-memory asyncio.Queue())
# 2. celery(multi-process w/ distributed task queue)
# 3. asyncio + pubsub mode (single-threaded; more overheads than asycnio+queu)
# 4. multi-threading (In Python, there is no true multi-threading due to GLI)
# 5. multi-processing (not suitable for I/O bounded task)

STOPWORD = "STOP"
TEST_URL = "https://example.com"

async def create_database():
    # Connect to SQLite database (or create it if it doesn't exist)
    connection = sqlite3.connect('proxy_verification.db')
    cursor = connection.cursor()

    # Create a table to store proxy information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            isValid BOOLEAN NOT NULL
        )
    ''')

    connection.commit()
    connection.close()

class RedisSender:

    def __init__(self, message_queue):
        self.message_queue = message_queue

    async def send_messages(self):
        redis_client = redis.StrictRedis()
        # proxy_source_path = os.path.join(
        #     os.path.dirname( __file__ ), "..", "sources", "socks5_proxy_sources.txt")
        proxy_source_path = os.path.join(
            os.path.dirname( __file__ ), "..", "proxy_sources.txt")
        with open(proxy_source_path, 'r') as file:
            proxy_source_list = file.readlines()
            for proxy_source in proxy_source_list:
                proxy_source_url = proxy_source.strip()
                try:
                    response = requests.get(
                        proxy_source_url,
                        timeout=5)
                    proxy_urls_string = response.text
                    if not proxy_urls_string:
                        continue
                    proxy_url_list = proxy_urls_string.split("\n")
                    for url in proxy_url_list:
                        await self.message_queue.put(url)
                        await asyncio.sleep(1)  # Simulate some processing time
                        # print(f"(Sender) Message Sent: {url}")
                except requests.exceptions.RequestException as e:
                    print(
                        f"Request error using {proxy_source_url}: {e}")
        await self.message_queue.put(STOPWORD)

class RedisReceiver:
    def __init__(self, message_queue):
        self.message_queue = message_queue
    
    async def record(self, proxy_ip, verification_result):
        # Insert proxy information into the database
        connection = sqlite3.connect('proxy_verification.db')
        cursor = connection.cursor()

        cursor.execute('''
            INSERT INTO proxies (ip, isValid) VALUES (?, ?)
        ''', (proxy_ip, verification_result))

        connection.commit()
        connection.close()

    async def validate(self, proxy_url):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False), trust_env=True) as session:
            try:
                async with session.get(TEST_URL, proxy=f'http://{proxy_url}', timeout=3) as response:
                    page_text = await response.text()
                    # print(page_text)
                    print('validated success: {}'.format(proxy_url))
            except Exception as e:
                print(e)
                print('error')
                return False
        return True

    async def receive_messages(self):
        while True:
            proxy_url = await self.message_queue.get()
            if proxy_url:
                print(f"(Receiver) Message Received: {proxy_url}")
                is_valid = await self.validate(proxy_url)
                await self.record(proxy_url, is_valid)
                if proxy_url == STOPWORD:
                    print("(Receiver) STOP")
                    break

async def main():
    key = "proxy_validation"
    import time
    start = time.time()
    # redis itself is a persistent queue
    message_queue = asyncio.Queue() # in-memory queue
    sender = RedisSender(message_queue)
    receiver = RedisReceiver(message_queue)

    sender_task = asyncio.create_task(sender.send_messages())
    receiver_task = asyncio.create_task(receiver.receive_messages())
    
    await create_database()
    await asyncio.gather(sender_task, receiver_task)
    
    end = time.time()
    print("total time spent: {}".format(end-start))
    await sender_task
    await receiver_task
   

if __name__ == "__main__":
    asyncio.run(main())
