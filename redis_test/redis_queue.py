import os
import asyncio
import redis.asyncio as redis
import requests

# 1. asyncio + queue (single-threaded)
# 2. celery(multi-process w/ distributed task queue)
# 3. asyncio + pubsub mode (single-threaded)
# 4. multi-threading
# 5. multi-processing

STOPWORD = "STOP"
class RedisSender:

    def __init__(self, message_queue):
        self.message_queue = message_queue

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
                        await self.message_queue.put(url)
                        print(f"(Sender) Message Sent: {url}")
                except requests.exceptions.RequestException as e:
                    print(
                        f"Request error using {proxy_source_url}: {e}")
        await self.message_queue.put(STOPWORD)
    # async def send_messages(self, messages):
    #     redis_client = redis.StrictRedis()
    #     for message in messages:
    #         await asyncio.sleep(1)  # Simulate some processing time
    #         redis_client.set(self.key, message)
    #         print(f"(Sender) Message Sent: {message}")
    #     redis_client.set(self.key, "STOP")

class RedisReceiver:
    def __init__(self, message_queue):
        self.message_queue = message_queue

    async def receive_messages(self):
        # redis_client = redis.StrictRedis()
        while True:
            # await asyncio.sleep(5)
            message = await self.message_queue.get()
            if message:
                # decoded_message = message.decode()
                # print(f"(Receiver) Message Received: {message}")
                if message == STOPWORD:
                    print("(Receiver) STOP")
                    break
            # await asyncio.sleep(0.1)

async def main():
    key = "communication_key"
    import time
    start = time.time()
    message_queue = asyncio.Queue()
    sender = RedisSender(message_queue)
    receiver = RedisReceiver(message_queue)

    # Start the receiver in the background
    receiver_task = asyncio.create_task(receiver.receive_messages())
    
    # Send messages from the sender
    
    await sender.send_messages()
    # await sender.send_messages(["Hello", "World", "How are you?"])
    end = time.time()
    print("total time spent: {}".format(end-start))
    # Wait for the receiver to finish
    await receiver_task

if __name__ == "__main__":
    asyncio.run(main())
