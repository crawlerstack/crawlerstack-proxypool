import asyncio

async def ppp():
    for i in range(5):
        await asyncio.sleep(1)
        print(i)


async def main():
    t = ppp()


def test_request():
    """"""
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    loop.run_forever()
