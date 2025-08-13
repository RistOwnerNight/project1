import asyncio, random, time
from typing import Callable, Iterable
def _jitter(base: float, spread: float) -> float: return base + random.uniform(0, spread)
async def a_retry(func, *, attempts=3, base=2.0, spread=0.5, on_retry: Callable[[int, Exception], None]|None=None, retry_for: Iterable[type]=()):
    for i in range(1, attempts+1):
        try: return await func()
        except Exception as e:
            if retry_for and not isinstance(e, tuple(retry_for)): raise
            if i == attempts: raise
            delay = _jitter(base**i, spread)
            if on_retry: on_retry(i, e)
            await asyncio.sleep(delay)
def retry(func, *, attempts=3, base=1.6, spread=0.4, on_retry: Callable[[int, Exception], None]|None=None, retry_for: Iterable[type]=()):
    for i in range(1, attempts+1):
        try: return func()
        except Exception as e:
            if retry_for and not isinstance(e, tuple(retry_for)): raise
            if i == attempts: raise
            delay = _jitter(base**i, spread)
            if on_retry: on_retry(i, e)
            time.sleep(delay)
