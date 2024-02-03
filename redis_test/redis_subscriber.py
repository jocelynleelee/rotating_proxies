import os
import time
import requests
import asyncio
import aiohttp
import sqlite3
import pydnsbl
import httpbl
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
            ip TEXT NOT NULL PRIMARY KEY,
            Dronebl JSON DEFAULT '{}',
            HttpPbl JSON DEFAULT '{}',
            Firehol JSON DEFAULT '{}',
            Dnsbl JSON DEFAULT '{}'
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

    async def check_proxy_exists(self, ip):
        result = None
        connection = sqlite3.connect('proxy_verification.db')
        cursor = connection.cursor()

        # Use a parameterized query to avoid SQL injection
        query = 'SELECT ip FROM proxies WHERE ip like "%{}%"'.format(ip)
        cursor.execute(query)
        
        # Fetch the result
        result = cursor.fetchone()

        connection.close()
        return result

    async def record(self, source, proxy_ip, verification_result):
        # Insert proxy information into the database
        connection = sqlite3.connect('proxy_verification.db')
        cursor = connection.cursor()
        result  = await self.check_proxy_exists(proxy_ip)
        if result is None:
            stmt = 'INSERT INTO proxies (ip, {}) VALUES ("{}", "{}")'.format(
                source, proxy_ip, verification_result
            )
        else:
            stmt = 'UPDATE proxies SET "{}" = "{}" WHERE ip = "{}"'.format(
                source, verification_result, proxy_ip)
            
        cursor.execute(stmt)
        connection.commit()
        connection.close()

class DroneblSubscriber(SanitizerSubscriber):

    async def validate(self, proxy_url):
        from dronebl import DroneBL
        d = DroneBL("04efa460cf244b6e88d9d2b8c31eb953")
        res = await d.lookuxp(proxy_url)
        await self.record("Dronebl", proxy_url, res)

class HttpPblSubscriber(SanitizerSubscriber):

    def __init__(self, channels):
        super().__init__(channels)
        self.bl = httpbl.HttpBL('mrxzvwbsbscd')

    async def validate(self, proxy_url):
        try:
            url = proxy_url.decode().split(":")[0]
            response = self.bl.query(url)

            print('IP Address: {}'.format(proxy_url))
            print('Threat Score: {}'.format(response['threat_score']))
            print('Days since last activity: {}'.format(response['days_since_last_activity']))
            if response.get("type"):
                print('Visitor type: {}'.format(', '.join([httpbl.DESCRIPTIONS[t] for t in response['type']])))
            await self.record("HttpPbl", proxy_url.decode(), response)
        except Exception as e:
            print(str(e))

class FireholSubscriber(SanitizerSubscriber):
    
    async def validate(self, proxy_url):
        pass

class DnsblSubscriber(SanitizerSubscriber):

    def __init__(self, channels):
        super().__init__(channels)
        self.ip_checker = pydnsbl.DNSBLIpChecker()
    
    async def validate(self, proxy_url):
        proxy_ip = proxy_url.decode().split(":")[0]
        res = await self.ip_checker.check_async(proxy_ip)
        res_dict = {"blacklisted": res.blacklisted,
                    "categories": res.categories,
                    "detected_by": res.detected_by}
        await self.record("Dnsbl", proxy_url.decode(), res_dict)
    
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
        time.sleep(1)
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
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
    
    async def publish(self, channel, message):
        await self.connection.publish(channel, message)
    
class SslProxiesPublisher(RedisPublisher):

    def __init__(self):
        super().__init__()
        self.proxy_list_url = "https://www.sslproxies.org/"

    async def get_proxies(self):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
            try:
                async with session.get(self.proxy_list_url, timeout=3) as response:
                    page_text = await response.text()
                    proxies = (page_text.split("\n"))[13:]
                    for proxy in proxies:
                        is_valid = await self.validate(proxy)
                        if not is_valid:
                            continue
                        await self.publish("channel:1", proxy)
                    
            except Exception as e:
                print(e)
                return False
        return True

class FreeProxyListPublisher(RedisPublisher):

    def __init__(self):
        super().__init__()
        self.proxy_list_url = "https://free-proxy-list.net/"

    async def get_proxies(self):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
            try:
                async with session.get(self.proxy_list_url, timeout=3) as response:
                    page_text = await response.text()
                    proxies = (page_text.split("\n"))[13:313]
                    for proxy in proxies:
                        is_valid = await self.validate(proxy)
                        if not is_valid:
                            continue
                        await self.publish("channel:1", proxy)
                    
            except Exception as e:
                print(e)
                return False
        return True

class UsProxyListPublisher(RedisPublisher):

    def __init__(self):
        super().__init__()
        self.proxy_list_url = "https://www.us-proxy.org/"

    async def get_proxies(self):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
            try:
                async with session.get(self.proxy_list_url, timeout=3) as response:
                    page_text = await response.text()
                    proxies = (page_text.split("\n"))[13:210]
                    for proxy in proxies:
                        is_valid = await self.validate(proxy)
                        if not is_valid:
                            continue
                        await self.publish("channel:1", proxy)
                    
            except Exception as e:
                print(e)
                return False
        return True

class SpyMeProxyPublisher(RedisPublisher):

    def __init__(self):
        super().__init__()
        self.proxy_list_url = "http://spys.me/proxy.txt"

    async def get_proxies(self):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
            try:
                async with session.get(self.proxy_list_url, timeout=3) as response:
                    page_text = await response.text()
                    proxies = (page_text.split("\n"))[9:-2]
                    for proxy in proxies:
                        proxy_ip = proxy.split(" ")
                        if len(proxy_ip) != 4:
                            continue
                        is_valid = await self.validate(proxy_ip[0])
                        if not is_valid:
                            continue
                        await self.publish("channel:1", proxy_ip[0])
                    
            except Exception as e:
                print(e)
                return False
        return True

class ProxyScrapePublisher(RedisPublisher):

    def __init__(self):
        super().__init__()
        self.proxy_list_url = "https://api.proxyscrape.com/?request=getproxies&proxytype=all&country=all&ssl=all&anonymity=all"

    async def get_proxies(self):
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(verify_ssl=True), trust_env=True) as session:
            try:
                async with session.get(self.proxy_list_url, timeout=3) as response:
                    page_text = await response.text()
                    proxies = (page_text.split("\r\n"))[:-1]
                    for proxy in proxies:
                        is_valid = await self.validate(proxy)
                        if not is_valid:
                            continue
                        await self.publish("channel:1", proxy)
                    
            except Exception as e:
                print(e)
                return False
        return True 

async def main():
    await create_database()
    publishers = [
        SslProxiesPublisher(),
        FreeProxyListPublisher(),
        UsProxyListPublisher(),
        SpyMeProxyPublisher(),
        ProxyScrapePublisher()
    ]
    subscribers = [
        HttpPblSubscriber(["channel:1"]),
        DnsblSubscriber(["channel:1"])]
    # subscriber = DnsblSubscriber(["channel:1"])
    subscriber_tasks = [asyncio.create_task(subscriber.subscribe()) for subscriber in subscribers]
    publisher_tasks = [asyncio.create_task(publisher.get_proxies()) for publisher in publishers]
    # subscriber_task = asyncio.create_task(subscriber.subscribe())
    await asyncio.gather(*subscriber_tasks, *publisher_tasks)

if __name__ == "__main__":
    asyncio.run(main())
    # import time
    # start = time.time()
    # subscriber = RedisSubscriber(["channel:1"])
    # sanitizer = SanitizerSubscriber(["channel:1"])
    # loop = asyncio.get_event_loop()
    # print("total time spent: {}".format(time.time()-start))