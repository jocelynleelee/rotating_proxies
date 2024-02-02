import asyncio
import pydnsbl
import redis.asyncio as redis

CHANNEL = "chat"

STOPWORD = "STOP"

# def check_dnsbl_blocking(proxy_url):
#     loop = asyncio.get_event_loop()
#     ip_checker = pydnsbl.DNSBLIpChecker()
#     return loop.run_in_executor(None, ip_checker.check, proxy_url)

async def consumer(redis_url, stop_event):
    redis_client = await redis.from_url(redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(CHANNEL)

    while not stop_event.is_set():
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message is not None:
            print(f"(Consumer) Message Received: {message}")
            res = await validate(message["data"])
            print(res)
            if message["data"].decode() == STOPWORD:
                print("(Consumer) STOP")
                stop_event.set()
                break

    pubsub.close()
    # await redis_client.wait_closed()

async def validate(proxy_url):
    import tracemalloc
    tracemalloc.start()
    url = "178.128.113.118"
    try:
        ip_checker = pydnsbl.DNSBLIpChecker()
        res = await ip_checker.check_async(url)
    except Exception as e:
        print(str(e))
    return res

async def producer(redis):
    for i in range(10):
        num = i
        # print(f"(Producer) Message Sent: {num}")
        await redis.publish(CHANNEL, num)
        # await asyncio.sleep(0.1)  # Adjust sleep time if needed
    await redis.publish(CHANNEL, STOPWORD)

async def main():
    redis_url = "redis://localhost"
    num_subscribers = 1

    # Use an event to signal the stop condition
    stop_event = asyncio.Event()

    # Create subscriber tasks
    subscriber_tasks = [consumer(redis_url, stop_event) for i in range(num_subscribers)]

    # Start the producer task
    redis_client = await redis.from_url(redis_url)
    producer_task = asyncio.create_task(producer(redis_client))

    # Wait for all tasks to finish
    await asyncio.gather(*subscriber_tasks, producer_task)

if __name__ == "__main__":
    import time
    start = time.time()
    asyncio.run(main())
    print("Time spent: {}".format(time.time() - start))
