import asyncio
from datetime import datetime

STOPWORD = "STOP"

"""
test redis queue with asyncio
"""
async def consumer(async_queue):
    while True:
        message = await async_queue.get()
        # message = await redis.lindex(channel, 0)
        if message:
            # message = message.decode()
            print("[{}] Consumer - Retrieved message: {}".format(datetime.now(), message))
            # await redis.lpop(channel)
            if message == STOPWORD:
                break


async def producer(async_queue):
    for i in range(1000):
        num = i
        print("[{}] Producer - Sending message number: {}".format(datetime.now(), num))
        await async_queue.put(num)
        await asyncio.sleep(0)
    await async_queue.put(STOPWORD)

async def main():
    message_queue = asyncio.Queue()
    channel = 'message_queue'

    consumer_task = asyncio.create_task(consumer(message_queue))
    producer_task = asyncio.create_task(producer(message_queue))

    await asyncio.gather(consumer_task, producer_task)
    

    # redis_client.close()
    # await redis_client.wait_closed()

if __name__ == "__main__":
    import time
    start = time.time()
    asyncio.run(main())
    print("time spent: {}".format(time.time()-start))
