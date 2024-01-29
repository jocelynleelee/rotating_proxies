import asyncio
import redis

class RedisSender:
    def __init__(self, key):
        self.key = key

    async def send_messages(self, messages):
        redis_client = redis.StrictRedis()
        for message in messages:
            await asyncio.sleep(1)  # Simulate some processing time
            redis_client.set(self.key, message)
            print(f"(Sender) Message Sent: {message}")
        redis_client.set(self.key, "STOP")

class RedisReceiver:
    def __init__(self, key):
        self.key = key

    async def receive_messages(self):
        redis_client = redis.StrictRedis()
        while True:
            message = redis_client.getdel(self.key)
            if message:
                decoded_message = message.decode()
                print(f"(Receiver) Message Received: {decoded_message}")
                if decoded_message == "STOP":
                    print("(Receiver) STOP")
                    break
            await asyncio.sleep(0.1)

async def main():
    key = "communication_key"

    sender = RedisSender(key)
    receiver = RedisReceiver(key)

    # Start the receiver in the background
    receiver_task = asyncio.create_task(receiver.receive_messages())

    # Send messages from the sender
    await sender.send_messages(["Hello", "World", "How are you?"])

    # Wait for the receiver to finish
    await receiver_task

if __name__ == "__main__":
    asyncio.run(main())
