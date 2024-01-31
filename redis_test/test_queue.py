import asyncio
import redis.asyncio as redis

STOPWORD = "STOP"

"""
test redis queue with asyncio
"""
async def consumer(redis, channel):
    while True:
        _, message = await redis.blpop(channel)
        # message = await redis.lindex(channel, 0)
        if message:
            message = message.decode()
            # print("Retrieved message: {}".format(message))
            # await redis.lpop(channel)
            if message == STOPWORD:
                break


async def producer(redis, channel):
    for i in range(100):
        num = i
        # print("Sending message number:  {}".format(num))
        await redis.rpush(channel, num)
        # await asyncio.sleep(0.5)
    await redis.lpush(channel, STOPWORD)
async def main():
    redis_client = await redis.from_url("redis://localhost")
    channel = 'message_queue'

    await asyncio.gather(consumer(redis_client, channel), producer(redis_client, channel))

    # redis_client.close()
    # await redis_client.wait_closed()

if __name__ == "__main__":
    import time
    start = time.time()
    asyncio.run(main())
    print("time spent: {}".format(time.time()-start))
