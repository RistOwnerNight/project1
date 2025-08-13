import logging
from asyncio import sleep
import eel
from telethon.errors import FloodWaitError

class AvoidFW:

    @staticmethod
    def avoid_floodwait(func):

        async def wrapper(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except FloodWaitError as fw:
                eel.log(f'(Floodwait) Сплю {fw.seconds + 3} секунд.')
                await sleep(fw.seconds + 3)
                await func(*args, **kwargs)
        return wrapper