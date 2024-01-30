import asyncio


async def consumer(q: asyncio.Queue):
    while True:
        msg = await q.get()
        print("Retrieved message:", msg)


async def producer(q: asyncio.Queue):
    for i in range(10):
        await q.put("Sending message number: {}".format(i+1))
        await asyncio.sleep(0.5)


async def main():
    q = asyncio.Queue()
    await asyncio.gather(consumer(q), producer(q))


if __name__ == "__main__":
    asyncio.run(main())
