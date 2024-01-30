import asyncio
import redis.asyncio as redis
CHANNEL = "chat"


async def consumer(c: redis.channel):
    while True:
        msg = await c.get()
        print("Message:", msg)


async def producer(r: redis.Redis):
    for i in range(10):
        await r.publish(CHANNEL, f"Sending message number: {i+1}")
        await asyncio.sleep(0.5)


async def main():
    redis = await redis.create_redis_pool(("localhost", 6379))
    ch, *_ = await redis.subscribe(CHANNEL)

    await asyncio.gather(consumer(ch), producer(redis))

    redis.close()


if __name__ == "__main__":
    asyncio.run(main())
