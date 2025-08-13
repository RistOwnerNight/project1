from asyncio import sleep
import random
from typing import List, Union
from telethon.errors import *
from core.account import TelegramAccount
from core.posts import Post, StickerPost
from telethon.tl.functions.help import GetPremiumPromoRequest
from telethon import functions

class AutoPosts:
    @staticmethod
    async def check_premium(client):
        return not (await client(GetPremiumPromoRequest())).status_text == 'By subscribing to Telegram Premium you agree to the Telegram Terms of Service and Privacy Policy.'

    @classmethod
    async def spam_old_posts(cls, telegram_account: TelegramAccount, posts: Union[Post, List[Post]], channels: List[str], spam_count: int=1, uniqalize_text: bool=False, delay: int=0):
        telegram_account.log_state('Обрабатываю комментарии старых постов!')
        is_premium = await AutoPosts.check_premium(telegram_account.telegram_client)
        for channel in channels:
            try:
                channel_entity = await telegram_account.telegram_client.get_entity(channel)
                it = telegram_account.telegram_client.iter_messages(channel_entity, limit=spam_count)
                async for message in it:
                    try:
                        post_to_send = random.choice(posts)
                        await post_to_send.answer_comment(message.id, message.peer_id, telegram_account.telegram_client, uniqalize_text)
                        telegram_account.log(f'({channel_entity.title}) Ответил.')
                    except FloodWaitError as fwe:
                        telegram_account.log_warning(f'({channel_entity.title}) Floodwait, сплю {fwe.seconds + 3} секунд.')
                        await sleep(fwe.seconds + 3)
                    except ChatGuestSendForbiddenError:
                        telegram_account.log_warning(f"({channel_entity.title}) Нужно вступить в чат прежде чем отправлять сообщения (возможно, заявку не успели принять).")
                        try:
                            discussion_group_id = message.replies.channel_id
                            await telegram_account.telegram_client(functions.channels.JoinChannelRequest(discussion_group_id))
                            await sleep(1)
                            await post_to_send.answer_comment(message.id, message.peer_id, telegram_account.telegram_client, uniqalize_text)
                            telegram_account.log(f'({channel_entity.title}) Ответил (после вступления в чат).')
                        except Exception:
                            pass
                    except UserBannedInChannelError:
                        telegram_account.log_warning(f'({channel_entity.title}) Вы были забанены в указанном канале.')
                        if is_premium: await telegram_account.remove_spamblock()
                    except (MsgIdInvalidError, ForbiddenError, ChannelPrivateError):
                        telegram_account.log_warning(f'({channel_entity.title}) У сообщения нет раздела с комментариями, или вы не можете писать в этот чат.')
                    except SlowModeWaitError as smwe:
                        telegram_account.log_warning(f'({channel_entity.title}) Включен медленный режим, жду {smwe.seconds} секунд.')
                        await sleep(smwe.seconds)
                    except ValueError:
                        telegram_account.log_warning(f'({channel}) Ошибка значения или неправильная ссылка.')
                
                telegram_account.log(f'({channel_entity.title}) Обработал все старые посты.')

            except FloodWaitError as fwe:
                telegram_account.log_warning(f'({channel}) Floodwait, сплю {fwe.seconds + 3} секунд.')
                await sleep(fwe.seconds + 3)
                continue
            except (ValueError, TypeError, ChannelInvalidError, ChatIdInvalidError, PeerIdInvalidError, InviteHashExpiredError, UsernameInvalidError, UsernameNotOccupiedError, RecursionError) as e:
                telegram_account.log_warning(f'({channel}) Не удалось найти канал/чат или неверный тип ссылки: {e.__class__.__name__}')
                continue
            
            await sleep(delay)