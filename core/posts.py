
import random
from typing import List, Union
from datetime import timedelta
import openai
import os
from telethon import TelegramClient, types
from telethon.tl.types import PeerChannel
from telethon.tl.functions.messages import GetAllStickersRequest, SendMessageRequest, GetDiscussionMessageRequest
from telethon.tl.functions.messages import GetStickerSetRequest
from telethon.tl.types import InputStickerSetID
from telethon.utils import get_message_id
from core.account import TelegramAccount
from plugins.uniqalize import Uniqalize

if os.path.exists('data/chatgpt.txt'):
    try:
        with open('./data/chatgpt.txt', mode='r', encoding='utf-8') as f:
            api_key = f.read().strip()
            if api_key:
                openai.api_key = api_key
    except (IOError, OSError) as e:
        print(f"Ошибка при чтении API ключа: {e}")

class Post:
    delay: timedelta
    send_as: int

    def __init__(self, delay=0):
        self.delay = timedelta(seconds=delay)

    async def answer_event(self, event, tgc, send_as=None):
        raise NotImplementedError()

    async def send(self, channel, tgc):
        raise NotImplementedError()

    async def answer_comment(self, msg_id, peer_id, tgc, uniqalize_text: bool=False):
        raise NotImplementedError()

    @staticmethod
    def from_dict(_dict: dict):
        raise NotImplementedError()

class AiPost(Post):
    prompt: str
    uniqalize_text: bool

    def __init__(self, prompt: str, delay: int=0):
        Post.__init__(self, delay)
        self.prompt = prompt

    async def send(self, tgc: TelegramClient, _id: int, uniqalize_text: bool=False):
        raise NotImplementedError

    async def answer_event(self, event, tgc, send_as=None, uniqalize_text: bool=False):
        response = ''
        messages = [{'role': 'user', 'content': self.prompt.replace('%p', event.message.raw_text)}]
        chat = openai.chat.completions.create(model='gpt-3.5-turbo', messages=messages)
        response = chat.choices[0].message.content
        response = Uniqalize.uniqalize_string(response) if uniqalize_text else response
        await tgc.send_message(entity=event.message.peer_id, message=response, comment_to=event.message, schedule=self.delay, parse_mode='md', link_preview=False)

    async def answer_comment(self, msg_id, peer_id, tgc, uniqalize_text: bool=False):
        raise NotImplementedError

class TextPost(Post):
    text: str

    def __init__(self, text: str, delay: int=0):
        Post.__init__(self, delay)
        self.text = text.replace('  ', '\n')

    async def send(self, tgc: TelegramClient, _id: int, uniqalize_text: bool=False):
        text = self.text if not uniqalize_text else Uniqalize.uniqalize_string(self.text)
        await tgc.send_message(entity=_id, message=Uniqalize.randomize_brackets(text), link_preview=False)

    async def answer_event(self, event, tgc, send_as=None, uniqalize_text: bool=False):
        text = self.text if not uniqalize_text else Uniqalize.uniqalize_string(self.text)
        file_path = './data/p.jpg'
        if os.path.exists(file_path):
            res = await tgc.send_message(entity=event.message.peer_id, file=file_path, message=Uniqalize.randomize_brackets(text), comment_to=event.message, schedule=self.delay, parse_mode='md', link_preview=False)
        else:
            res = await tgc.send_message(entity=event.message.peer_id, message=Uniqalize.randomize_brackets(text), comment_to=event.message, schedule=self.delay, parse_mode='md', link_preview=False)

    async def answer_comment(self, msg_id, peer_id, tgc, uniqalize_text: bool=False):
        text = self.text if not uniqalize_text else Uniqalize.uniqalize_string(self.text)
        file_path = './data/p.jpg'
        if os.path.exists(file_path):
            await tgc.send_file(peer_id, file=file_path, caption=Uniqalize.randomize_brackets(text), comment_to=msg_id, schedule=self.delay, parse_mode='md', link_preview=False)
        else:
            await tgc.send_message(peer_id, Uniqalize.randomize_brackets(text), comment_to=msg_id, schedule=self.delay, parse_mode='md', link_preview=False)
        return None

class StickerPost(Post):

    @staticmethod
    def from_dict(_dict: dict):
        return

    def __init__(self, delay: int=0):
        Post.__init__(self, delay)
        self.stickers = None

    async def send(self, tgc: TelegramClient, _id: int, uniqalize_text: bool=False):
        await tgc.send_message(entity=_id, file='CAACAgIAAxkBAAEMuFhmzgHgGLts-g2Ikx1B6hWUuUJmBQACMhcAAjIp2ElVz-fxiTWL8zUE', link_preview=False)

    async def answer_event(self, event, tgc, send_as=None, uniqalize_text: bool=False):
        await tgc.send_file(event.message.peer_id, 'CAACAgIAAxkBAAEMuFhmzgHgGLts-g2Ikx1B6hWUuUJmBQACMhcAAjIp2ElVz-fxiTWL8zUE', comment_to=event.message)

    async def answer_comment(self, msg_id, peer_id, tgc, uniqalize_text: bool=False):
        await tgc.send_file(peer_id, 'CAACAgIAAxkBAAEMuFhmzgHgGLts-g2Ikx1B6hWUuUJmBQACMhcAAjIp2ElVz-fxiTWL8zUE')

