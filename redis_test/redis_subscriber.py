import os
import requests
import asyncio
import aiohttp
import sqlite3
import redis.asyncio as redis
# pubsub vs queue
# https://www.linkedin.com/pulse/pubsub-system-vs-queues-osama-ahmed/
STOPWORD = "STOP"
TEST_URL = "https://example.com"

async def create_database():
    connection = sqlite3.connect('proxy_verification.db')
    cursor = connection.cursor()

    # Create a table to store proxy information
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proxies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            Dronebl TEXT,
            HttpPbl TEXT,
            Firehol TEXT,
            Dnsbl TEXT
        )
    ''')

    connection.commit()
    connection.close()

class RedisSubscriber:
    def __init__(self, channels):
        self.channels = channels

    async def subscribe(self):
        self.connection = redis.from_url("redis://localhost")
        async with self.connection.pubsub() as pubsub:
            await pubsub.subscribe(*self.channels)
            await self.listen(pubsub)

    async def listen(self, pubsub):
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message is not None:
                print(f"(Subscriber) Message Received: {message}")
                if message["data"].decode() == STOPWORD:
                    print("(Subscriber) STOP")
                    break


class SanitizerSubscriber:
    """
    verify all proxy urls
    """
    def __init__(self, channels):
        self.channels = channels

    async def subscribe(self):
        self.connection = redis.from_url("redis://localhost")
        async with self.connection.pubsub() as pubsub:
            await pubsub.subscribe(*self.channels)
            await self.listen(pubsub)

    async def listen(self, pubsub):
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message is not None:
                print(f"(SanitizerSubscriber) Message Received: {message}")
                if message["data"].decode() == STOPWORD:
                    print("(Subscriber) STOP")
                    break
                proxy_ip = message["data"]
                await self.validate(proxy_ip)

    async def validate(self, proxy_url):
        pass

class DroneblSubscriber(SanitizerSubscriber):

    async def validate(self, proxy_url):
        from dronebl import AsyncDroneBL
        d = AsyncDroneBL("04efa460cf244b6e88d9d2b8c31eb953")
        await d.lookup(proxy_url)

class HttpPblSubscriber(SanitizerSubscriber):

    async def validate(self, proxy_url):
        import httpbl
        bl = httpbl.HttpBL('mrxzvwbsbscd')
        response = bl.query(proxy_url)

        print('IP Address: {}'.format(proxy_url))
        print('Threat Score: {}'.format(response['threat_score']))
        print('Days since last activity: {}'.foramt(response['days_since_last_activity']))
        print('Visitor type: {}'.format(', '.join([httpbl.DESCRIPTIONS[t] for t in response['type']])))


class FireholSubscriber(SanitizerSubscriber):
    
    async def validate(self, proxy_url):
        pass

class DnsblSubscriber(SanitizerSubscriber):
    
    async def validate(self, proxy_url):
        import pydnsbl
        ip_checker = pydnsbl.DNSBLIpChecker()
        ip_checker.check(proxy_url)
    

class RedisPublisher:
    def __init__(self):
        self.connection = redis.from_url("redis://localhost")

    async def send_messages(self):
        redis_client = redis.StrictRedis()
        proxy_source_path = os.path.join(
            os.path.dirname( __file__ ), "..", "sources", "socks5_proxy_sources.txt")
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
                        # await asyncio.sleep(1)  # Simulate some processing time
                        # await self.publish("channel:1", url)
                        is_valid = await self.validate(url)
                        if is_valid:
                            await self.publish("channel:1", url)
                        # print(f"(Sender) Message Sent: {url}")
                except requests.exceptions.RequestException as e:
                    print(
                        f"Request error using {proxy_source_url}: {e}")
        await self.publish("channel:1", STOPWORD)
    
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


 
async def run_publisher():
    publisher = RedisPublisher()
    await publisher.send_messages()


async def main():
    await create_database()
    publisher = RedisPublisher()
    subscribers = [
        HttpPblSubscriber(["channel:1"]),
        DnsblSubscriber(["channel:1"])]
    subscriber_tasks = [asyncio.create_task(subscriber.subscribe()) for subscriber in subscribers]
    producer_task = asyncio.create_task(publisher.send_messages())

    await asyncio.gather(*subscriber_tasks, producer_task)

if __name__ == "__main__":
    import time
    start = time.time()
    # subscriber = RedisSubscriber(["channel:1"])
    # sanitizer = SanitizerSubscriber(["channel:1"])
    # loop = asyncio.get_event_loop()

    asyncio.run(main())
    print("total time spent: {}".format(time.time()-start))