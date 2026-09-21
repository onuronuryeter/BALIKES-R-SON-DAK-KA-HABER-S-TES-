import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        try:
            r1 = await client.get('http://127.0.0.1:8000/arsiv')
            print('/arsiv:', r1.status_code)
        except Exception as e:
            print('/arsiv: FAIL', e)
            
        try:
            r2 = await client.get('http://127.0.0.1:8000/kategori/karesi')
            print('/kategori/karesi:', r2.status_code)
        except Exception as e:
            print('/kategori/karesi: FAIL', e)

if __name__ == "__main__":
    asyncio.run(test())
