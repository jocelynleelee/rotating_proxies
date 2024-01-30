import asyncio
import redis.asyncio as redis

async def consumer(redis, channel):
    while True:
        message = await redis.brpoplpush(channel, channel, timeout=0)
        if message:
            print("Retrieved message:", message.decode())

async def producer(redis, channel):
    for i in range(10):
        message = "Sending message number: {}".format(i + 1)
        await redis.lpush(channel, message)
        await asyncio.sleep(0.5)

async def main():
    redis_client = await redis.from_url("redis://localhost")
    channel = 'message_queue'

    await asyncio.gather(consumer(redis_client, channel), producer(redis_client, channel))

    redis_client.close()
    await redis_client.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())
