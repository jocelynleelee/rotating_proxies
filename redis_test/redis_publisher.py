import asyncio
import redis.asyncio as async_redis

class AsyncMessageSubscriber:
    def __init__(self, redis_host='localhost', redis_port=6379, channel='tasks_channel'):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.channel = channel

    async def process_messages(self):
        redis_uri = f'redis://{self.redis_host}:{self.redis_port}'
        pool = async_redis.ConnectionPool.from_url("redis://localhost")
        r = await async_redis.from_url("redis://localhost")
        # Subscribe to the Redis channel
        async with r.pubsub() as pubsub:
            await pubsub.psubscribe("channel:*")

        # async for message in channel.iter(encoding='utf-8'):
        #     # Process the received message
        #     print(f"Received message: {message}")

        # r.close()
        # await r.wait_closed()

# Example usage
async_subscriber = AsyncMessageSubscriber()
asyncio.run(async_subscriber.process_messages())
