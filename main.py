import asyncio
import json
import os
import random
import traceback
from typing import List, Union
import eel
from core.logger import bind_eel, info, warn, error
from core.config_validator import validate_config
import pythoncom
from telethon.tl.functions.channels import CreateChannelRequest, UpdateUsernameRequest, EditPhotoRequest, DeleteChannelRequest
from telethon.tl.functions.account import UpdatePersonalChannelRequest
from telethon.tl.types import MessageActionChatEditPhoto
from telethon.errors import UserRestrictedError, ChannelsAdminPublicTooMuchError, UserDeactivatedBanError, AuthKeyUnregisteredError, BadRequestError, FloodWaitError
from sqlite3 import OperationalError
from types import NoneType
from sqlite3 import OperationalError, InterfaceError
import core.eeltun as eelp
from core.account import TelegramAccount
from core.posts import TextPost, AiPost
from core.autofiles import Files
from plugins.autocomments import AutoComments
from plugins.autoposts import AutoPosts
from plugins.autoprofile import AutoProfile
from plugins.fishing import Fishing
from plugins.autoreply import AutoReply

class TelegramCommentsEnhanced:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    accounts: List[TelegramAccount] = []
    task: Union[asyncio.Task, None] = None

    @staticmethod
    def parse_posts(config_posts) -> List[Union[TextPost, AiPost]]:
        posts = []
        for entry in config_posts:
            try:
                delay = int(entry[entry.index('(') + 1:entry.index('s)')])
                text = entry[entry.index(')') + 2:].replace('\\n', '\n')
                posts.append(AiPost(text, delay=delay) if entry.startswith('AI') else TextPost(text, delay=delay))
            except ValueError:
                posts.append(TextPost(entry.replace('\\n', '\n')))
        return posts

    async def _clear_old_channels(self, account: TelegramAccount, keep_channel_id: int):
        account.log_error("Аккаунт достиг лимита каналов. Запускаю очистку...")
        owned_channels = [d.entity for d in await account.telegram_client.get_dialogs() if getattr(d.entity, 'creator', False)]
        if not owned_channels:
            account.log_warning("Не найдено каналов для удаления.")
            return
        owned_channels.sort(key=lambda c: c.date)
        for channel in owned_channels:
            if channel.id == keep_channel_id:
                continue
            try:
                account.log_state(f"Удаляю канал: {channel.title} (ID: {channel.id})")
                await account.telegram_client(DeleteChannelRequest(channel=channel.id))
                account.log_warning("Удален 1 канал.")
                return
            except Exception as e:
                account.log_error(f"Не удалось удалить канал {channel.title}: {e}")

    async def launch(self, timing: str):
        if self.task and not self.task.done():
            self.task.cancel()
            try: await self.task
            except asyncio.CancelledError: pass
            self.task = None
        for acc in self.accounts:
            if acc.telegram_client and acc.telegram_client.is_connected():
                acc.log_warning("Отключаю активный клиент...")
                try:
                    await acc.telegram_client.disconnect()
                except FloodWaitError as fwe:
                    acc.log_warning(f"FloodWait: ждём {getattr(fwe, 'seconds', 60)} сек.")
                    await asyncio.sleep(getattr(fwe, 'seconds', 60) + 1)
                except Exception as e:
                    acc.log_error(f'Ошибка при отключении: {e}')
        await self._launch(timing)

    async def _launch(self, timing: str):
        try:
            self.accounts = []
            pythoncom.CoInitialize()
            with open('./data/config.json', encoding='utf-8') as f:
                config = json.load(f)
            for filename in os.listdir('./data/accounts/'):
                if filename.endswith('.session'):
                    jsf = filename.replace('.session', '.json')
                    if not os.path.isfile(f'./data/accounts/{jsf}'):
                        with open(f'./data/accounts/{jsf}', 'w', encoding='utf-8') as f_json:
                            f_json.write(json.dumps({
                                "first_name": "DEFAULT", "last_name": "DEFAULT",
                                "phone": filename.replace('.session', ''),
                                "app_id": 2040, "app_hash": "b18441a1ff607e10a989891a5462e627",
                                "session_file": filename.replace('.session', ''),
                                "device": "Desktop", "sdk": "Windows 10",
                                "app_version": "4.2.2 x64", "lang_pack": "en",
                                "system_lang_pack": "en-US", "joined_channels": []
                            }))
                        eel.log_warning(f'Сконвертировал session в json + session. ({filename}).')
                elif filename.endswith('.json'):
                    self.accounts.append(TelegramAccount.from_file(f'./data/accounts/{filename}'))
            if not self.accounts:
                eel.log_error('Сначала загрузите аккаунт в ./data/accounts/.')
                return

            acc = self.accounts[0]
            try:
                await acc.telegram_client.connect()
                await acc.check_account_info()
                if config['profile']['hidden']:
                    await Fishing.prepare_account(acc, config['profile']['fa'])
                if os.path.exists('data/autoreply.txt'):
                    with open('data/autoreply.txt', 'r', encoding='utf-8') as f_autoreply:
                        await AutoReply.handle_new_messages(acc, f_autoreply.read())
                if config['autojoin']['enabled']:
                    acc.log_state('Вступаю в каналы!')
                    delay = str(config['autojoin']['delay'])
                    try:
                        if '-' in delay:
                            parts = delay.split('-')
                            min_d, max_d = int(parts[0]), int(parts[1])
                        else:
                            min_d = max_d = int(delay)
                    except (ValueError, IndexError):
                        min_d = max_d = 90
                    await acc.participate(config['autojoin']['channels'], should_hide=config['profile']['hidden'], min_delay=min_d, max_delay=max_d)
                    acc.log_state('Вступил во все каналы.')
                if config['profile']['enabled']:
                    pic = None
                    try:
                        pics_dir = './data/profile_pics/'
                        if os.path.exists(pics_dir) and os.listdir(pics_dir):
                            pic = os.path.join(pics_dir, random.choice(os.listdir(pics_dir)))
                        else:
                            acc.log_warning('Нет фото в data/profile_pics/.')
                    except Exception as e:
                        acc.log_error(f'Ошибка при выборе фото: {e}')
                    await AutoProfile.update_info(acc, config['profile']['first_name'], config['profile']['last_name'],
                        config['profile']['bio'], config['profile']['username'], pic, config['profile']['hidden'])
                    # Привязанный канал
                    def readfile(path): return open(path, 'r', encoding='utf-8').read().strip() if os.path.exists(path) else ''
                    cname, cbio, cusername, ptext = map(readfile, [
                        'data/linked_channel/channel_name.txt',
                        'data/linked_channel/channel_bio.txt',
                        'data/linked_channel/channel_username.txt',
                        'data/linked_channel/post_text.txt'
                    ])
                    if cname:
                        acc.log_state('[Привязанный канал] Создаю канал!')
                        try:
                            result = await acc.telegram_client(CreateChannelRequest(cname, cbio))
                            channel_id = next((getattr(u, 'channel_id', None) for u in result.updates if hasattr(u, 'channel_id')), None)
                            if not channel_id:
                                try: channel_id = result.updates[1].channel_id
                                except Exception: acc.log_error('Не удалось получить ID канала.'); channel_id = None
                            if channel_id:
                                channel_entity = await acc.telegram_client.get_entity(channel_id)
                                try:
                                    while '%' in cusername:
                                        cusername = cusername.replace('%', random.choice('abcdefghijklmnopqrstuvwxyz'), 1)
                                    await acc.telegram_client(UpdateUsernameRequest(channel_entity, cusername))
                                except ChannelsAdminPublicTooMuchError:
                                    await self._clear_old_channels(acc, keep_channel_id=channel_id)
                                    try: await acc.telegram_client(UpdateUsernameRequest(channel_entity, cusername))
                                    except Exception as e: acc.log_error(f'Не удалось установить юзернейм после очистки: {e}')
                                photo_path = 'data/linked_channel/channel_photo.png'
                                if os.path.exists(photo_path):
                                    try:
                                        uploaded_photo = await acc.telegram_client.upload_file(photo_path)
                                        await acc.telegram_client(EditPhotoRequest(channel=channel_entity, photo=uploaded_photo))
                                        await asyncio.sleep(2)
                                        async for message in acc.telegram_client.iter_messages(channel_entity, limit=5):
                                            if message.action and isinstance(message.action, MessageActionChatEditPhoto):
                                                await message.delete(); break
                                    except Exception as e:
                                        acc.log_error(f"[Привязанный канал] Не удалось установить аватарку: {e}")
                                else:
                                    acc.log_warning('[Привязанный канал] channel_photo.png не найден.')
                                await acc.telegram_client(UpdatePersonalChannelRequest(channel=channel_entity))
                                post_photo_path = 'data/linked_channel/post_photo.png'
                                if os.path.exists(post_photo_path):
                                    await acc.telegram_client.send_file(channel_entity, file=post_photo_path, caption=ptext)
                                elif ptext:
                                    await acc.telegram_client.send_message(channel_entity, ptext)
                        except UserRestrictedError:
                            acc.log_error('[Привязанный канал] Аккаунт ограничен Telegram - создание каналов запрещено.')
                        except ChannelsAdminPublicTooMuchError:
                            acc.log_error('[Привязанный канал] Превышен лимит каналов.')
                        except Exception as e:
                            acc.log_error(f'[Привязанный канал] Ошибка при создании канала: {e.__class__.__name__}')
                if isinstance(timing, NoneType): return
                eel.start_timing('🚀')
                if config['autoposts']['enabled']:
                    posts = self.parse_posts(config['autoposts']['posts'])
                    delay = str(config['autoposts']['delay'])
                    try:
                        if '-' in delay:
                            parts = delay.split('-')
                            min_d, max_d = int(parts[0]), int(parts[1])
                        else:
                            min_d = max_d = int(delay)
                    except (ValueError, IndexError):
                        min_d = max_d = 90
                    delay_val = 5 if (min_d == 0 and max_d == 0 and not delay.isdigit()) else (random.randint(min_d, max_d) if min_d <= max_d else min_d)
                    await AutoPosts.spam_old_posts(acc, posts, config['autoposts']['channels'], int(config['autoposts']['count']), config['autoposts']['uniqalize'], delay_val)
                if config['autocomments']['enabled']:
                    posts = self.parse_posts(config['autocomments']['posts'])
                    await AutoComments.handle_comments(acc, posts, config['autocomments']['uniqalize'], hidden=config['profile']['hidden'], spam_all=config['autojoin']['all'])
                await acc.telegram_client.run_until_disconnected()
            except UserDeactivatedBanError:
                acc.log_error('Требуется замена аккаунта (деактивирован защитой Telegram).')
                await acc.telegram_client.disconnect()
            except AuthKeyUnregisteredError:
                acc.log_error('Аккаунт удален или сессия отозвана.')
                await acc.telegram_client.disconnect()
            except BadRequestError as e:
                if 'FROZEN_PARTICIPANT_MISSING' in str(e):
                    acc.log_error('Аккаунт заморожен или ограничен в правах.')
                else:
                    acc.log_error(f'Ошибка запроса: {e}')
                await acc.telegram_client.disconnect()
            except (OperationalError, InterfaceError) as e:
                if isinstance(e, InterfaceError):
                    acc.log_error('Сессия повреждена или аккаунт заблокирован.')
                else:
                    acc.log_error(f'Требуется замена сессии (сессия повреждена, аккаунт всё ещё рабочий, возможно 1 софт запущен 2 раза). Ошибка: {e}')
                await acc.telegram_client.disconnect()
            except Exception as e:
                acc.log_error(f'Неизвестная ошибка во время работы аккаунта: {e.__class__.__name__}')
                for l in traceback.format_exc().splitlines():
                    acc.log_error(l)
                await acc.telegram_client.disconnect()
        except Exception as e:
            eel.log_error(f'Неизвестная ошибка при запуске: {e.__class__.__name__}')
            for l in traceback.format_exc().splitlines():
                eel.log_error(l)

if __name__ == '__main__':
    try:
        print("Запуск программы...")
        Files.create_file_structure()
        print("Файловая структура создана...")
        bind_eel(eel)
        ok, errs = validate_config('data/config.json')
        if not ok:
            for m in errs:
                try: eel.log_warning(m)
                except Exception: pass
        eelp.EelTunnel.start()
        print("EelTunnel запущен...")
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        traceback.print_exc()
        input("Нажмите Enter для выхода...")