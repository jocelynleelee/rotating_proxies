import os
import requests
import asyncio
import redis.asyncio as redis
# pubsub vs queue
# https://www.linkedin.com/pulse/pubsub-system-vs-queues-osama-ahmed/
STOPWORD = "STOP"

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



class RedisPublisher:
    def __init__(self):
        self.connection = redis.from_url("redis://localhost")

    async def send_messages(self):
        redis_client = redis.StrictRedis()
        # proxy_source_path = os.path.join(
        #     os.path.dirname( __file__ ), "..", "sources", "socks5_proxy_sources.txt")
        proxy_source_path = os.path.join(
            os.path.dirname( __file__ ), "..", "proxy_list.txt")
        with open(proxy_source_path, 'r') as file:
            proxy_source_list = file.readlines()
            for proxy_source in proxy_source_list:
                proxy_source_url = proxy_source.strip()
                try:
                    # response = requests.get(
                    #     proxy_source_url,
                    #     timeout=5)
                    # proxy_urls_string = response.text
                    # if not proxy_urls_string:
                    #     continue
                    proxy_url_list = proxy_source_url.split("\n")
                    for url in proxy_url_list:
                        # await asyncio.sleep(1)  # Simulate some processing time
                        await self.publish("channel:1", url)
                        # print(f"(Sender) Message Sent: {url}")
                except requests.exceptions.RequestException as e:
                    print(
                        f"Request error using {proxy_source_url}: {e}")
        await self.publish("channel:1", STOPWORD)
    
    async def publish(self, channel, message):
        await self.connection.publish(channel, message)


 
async def run_publisher():
    publisher = RedisPublisher()
    await publisher.send_messages()


async def main():
    publisher = RedisPublisher()
    subscribers = [
        RedisSubscriber(["channel:1"]),
        SanitizerSubscriber(["channel:1"])]
    subscriber_tasks = [asyncio.create_task(subscriber.subscribe()) for subscriber in subscribers]
    producer_task = asyncio.create_task(publisher.send_messages())
    # subscriber2_task = asyncio.create_task(SanitizerSubscriber(["channel:1"]))
    # Run subscriber in the background
    # subscriber_task = loop.create_task(subscriber.subscribe())

    # # Run publisher tasks
    # loop.run_until_complete(run_publisher())

    # # Wait for the subscriber to finish
    # loop.run_until_complete(subscriber_task)

    await asyncio.gather(*subscriber_tasks, producer_task)

if __name__ == "__main__":
    import time
    start = time.time()
    # subscriber = RedisSubscriber(["channel:1"])
    # sanitizer = SanitizerSubscriber(["channel:1"])
    # loop = asyncio.get_event_loop()

    asyncio.run(main())
    print("total time spent: {}".format(time.time()-start))