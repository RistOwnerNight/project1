import datetime
from asyncio import sleep
from typing import Union, List

from telethon.errors import (
    UserAlreadyParticipantError, ChannelsTooMuchError, InviteHashEmptyError,
    InviteHashExpiredError, InviteHashInvalidError, ChannelInvalidError,
    ChannelPrivateError, UsernameInvalidError, FloodWaitError, InviteRequestSentError
)
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest, JoinChatlistInviteRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import InputPeerNotifySettings, NotificationSoundDefault

from core.account import TelegramAccount
from plugins.avoidfw import AvoidFW


class AutoJoin:

    @staticmethod
    async def join(telegram_account: TelegramAccount, link_or_username: Union[str, List[str]], delay: float = 0, hidden: bool = False):
        
        telegram_account.log_state('Вступаю в каналы!')
        
        links_to_process = []
        if isinstance(link_or_username, list):
            links_to_process = link_or_username
            
            if telegram_account.last_joined_channel and telegram_account.last_joined_channel in links_to_process:
                try:
                    start_index = links_to_process.index(telegram_account.last_joined_channel) + 1
                    links_to_process = links_to_process[start_index:]
                except ValueError:

                    pass
        elif isinstance(link_or_username, str):
            links_to_process = [link_or_username]

        for link in links_to_process:
            try:
                await AutoJoin._join(telegram_account, link, hidden=hidden)
                if len(links_to_process) > 1:
                    await sleep(delay)
            except ChannelsTooMuchError:
                telegram_account.log_warning('Аккаунт присоединился к слишком большому количеству каналов/супергрупп.')
                break  

        telegram_account.log('Вступил во все заданные каналы.')

    @staticmethod
    @AvoidFW.avoid_floodwait
    async def _join(telegram_account: TelegramAccount, link_or_username: Union[str, int], hidden: bool = False, _sleep: bool = True):

        if isinstance(link_or_username, str):
            telegram_account.last_joined_channel = link_or_username
            telegram_account.to_file()

        try:
            res = None

            if isinstance(link_or_username, int):
                telegram_account.log(f'({link_or_username}) Для написания комментария нужно вступить в чат.')
                res = await telegram_account.telegram_client(JoinChannelRequest(link_or_username))

            elif link_or_username.startswith(('https://t.me/addlist/', 't.me/addlist/')):
                slug = link_or_username.split('/')[-1]
                invite = await telegram_account.telegram_client(CheckChatlistInviteRequest(slug=slug))
                await telegram_account.telegram_client(JoinChatlistInviteRequest(slug=slug, peers=invite.peers))
                telegram_account.log(f"Успешно вступил в каналы из папки: {link_or_username}")
                return  
            elif link_or_username.startswith(('https://t.me/+', 't.me/+', 'https://t.me/joinchat/', 't.me/joinchat/')):
                invite_hash = link_or_username.replace('https://t.me/+', '').replace('t.me/+', '').replace('https://t.me/joinchat/', '').replace('t.me/joinchat/', '')
                res = await telegram_account.telegram_client(ImportChatInviteRequest(hash=invite_hash))
            else:
                res = await telegram_account.telegram_client(JoinChannelRequest(channel=link_or_username))
            if res and hasattr(res, 'chats') and res.chats:
                chat = res.chats[0]
                telegram_account.joined_channels.append(chat.id)
                telegram_account.to_file()
                telegram_account.log(f'([{link_or_username}]({chat.title})) Вступил.')

                if hidden:
                    
                    await telegram_account.telegram_client(UpdateNotifySettingsRequest(
                        peer=chat,
                        settings=InputPeerNotifySettings(
                            show_previews=False,
                            mute_until=datetime.datetime(2025, 1, 1),
                            sound=NotificationSoundDefault()
                        )
                    ))
                    await telegram_account.telegram_client.edit_folder(chat, 1)  # 1 = Archive
                    telegram_account.log(f'([{link_or_username}]({chat.title})) Добавлено в архив и уведомления выкл.')
        except UserAlreadyParticipantError:
            telegram_account.log_warning(f'([{link_or_username}]) Пользователь уже является участником чата.')
        except InviteHashEmptyError:
            telegram_account.log_warning(f'([{link_or_username}]) Хэш приглашения пуст.')
        except InviteHashExpiredError:
            telegram_account.log_warning(f'([{link_or_username}]) Срок действия приглашения истёк.')
        except InviteHashInvalidError:
            telegram_account.log_warning(f'([{link_or_username}]) Хэш приглашения недействителен.')
        except ChannelInvalidError:
            telegram_account.log_warning(f'([{link_or_username}]) Недопустимый объект канала.')
        except ChannelPrivateError:
            telegram_account.log_warning(f'([{link_or_username}]) Канал частный или вы забанены.')
        except UsernameInvalidError:
            telegram_account.log_warning(f'([{link_or_username}]) Неверное имя пользователя.')
        except InviteRequestSentError:
            telegram_account.log_warning(f'([{link_or_username}]) Запрос на вступление уже отправлен.')
        except FloodWaitError as e:

            if _sleep:
                wait_time = e.seconds + 3
                telegram_account.log_warning(f'([{link_or_username}]) Floodwait, сплю {wait_time} секунд.')
                await sleep(wait_time)
            else:
                telegram_account.log_warning(f'([{link_or_username}]) Floodwait, пропуск.')
                raise e  
        except (ValueError, TypeError) as e:
            telegram_account.log_warning(f'([{link_or_username}]) Не удалось найти канал/чат или неверный тип ссылки: {e}')