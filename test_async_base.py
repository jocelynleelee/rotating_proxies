import asyncio
import aiosocks
import aiohttp

async def send(proxy: str, url: str):
    '''Proxy can be in IP:PORT format or USER:PASS@IP:PORT format'''
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False), trust_env=True) as session:
        try:
            async with session.get(url,
             proxy="http://" + proxy , timeout=10) as response:
                page_text = await response.text()
                print(page_text)
                print('success')
        except Exception as e:
            print(e)
            print('error')

if __name__ == "__main__":
    asyncio.run(send("144.202.41.55:39162", "https://example.com"))