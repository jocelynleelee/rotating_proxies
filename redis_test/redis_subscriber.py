import asyncio
import redis.asyncio as redis

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


class RedisPublisher:
    def __init__(self):
        self.connection = redis.from_url("redis://localhost")

    async def publish(self, channel, message):
        await self.connection.publish(channel, message)

async def run_publisher():
    publisher = RedisPublisher()
    await publisher.publish("channel:1", "Hello")
    await publisher.publish("channel:2", "World")
    await publisher.publish("channel:1", STOPWORD)

if __name__ == "__main__":
    subscriber = RedisSubscriber(["channel:1", "channel:2"])
    loop = asyncio.get_event_loop()

    # Run subscriber in the background
    subscriber_task = loop.create_task(subscriber.subscribe())

    # Run publisher tasks
    loop.run_until_complete(run_publisher())

    # Wait for the subscriber to finish
    loop.run_until_complete(subscriber_task)