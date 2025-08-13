import sys
import random
import traceback
import asyncio
from typing import Union, List

from telethon import events, functions
from telethon.errors import *
from telethon.tl.functions.help import GetPremiumPromoRequest

from core.posts import Post
from core.account import TelegramAccount

class AutoComments:

    @staticmethod
    async def check_premium(client):
        try:
            promo = await client(GetPremiumPromoRequest())
            return not promo.status_text == 'By subscribing to Telegram Premium you agree to the Telegram Terms of Service and Privacy Policy.'
        except:
            return False

    @staticmethod
    async def handle_comments(telegram_account: TelegramAccount, posts: Union[Post, List[Post]], uniqalize_text: bool = False, hidden: bool = False, spam_all: bool = True):
        # Проверяем, был ли обработчик уже зарегистрирован
        if hasattr(telegram_account, '_autocomments_handler_registered') and telegram_account._autocomments_handler_registered:
            telegram_account.log_state('Модуль автокомментирования уже активен.')
            return

        telegram_account.log_state('Обрабатываю комментарии новых постов!')
        is_premium = await AutoComments.check_premium(telegram_account.telegram_client)

        @telegram_account.telegram_client.on(events.NewMessage)
        async def _handle_new_post(event):
            try:
                # Начальные проверки: не наше сообщение, это пост в канале, есть комменты, канал в списке
                if event.message.out: return
                if not event.chat: return  # Проверяем что event.chat существует
                if not (event.is_channel and event.chat.broadcast): return
                if event.message.replies is None: return
                if not spam_all and event.chat_id not in telegram_account.joined_channels: return

                post_to_send = random.choice(posts)
                
                # --- УМНАЯ ЛОГИКА ОТПРАВКИ ---
                try:
                    # 1. Оптимистичная попытка отправить комментарий сразу
                    await post_to_send.answer_event(event, telegram_account.telegram_client, uniqalize_text=uniqalize_text)
                    telegram_account.log(f'({event.chat.title}) Успешно оставлен комментарий.')

                except ChatGuestSendForbiddenError:
                    # 2. Попытка провалилась, потому что мы "гость". Теперь вступаем.
                    telegram_account.log_warning(f"({event.chat.title}) Доступ для гостей запрещен. Пробую вступить в чат...")
                    
                    try:
                        discussion_group_id = event.message.replies.channel_id
                        await telegram_account.telegram_client(functions.channels.JoinChannelRequest(discussion_group_id))
                        telegram_account.log(f"({event.chat.title}) Успешно вступил в чат для комментариев. Повторная отправка...")
                        
                        # Даем Telegram секунду на обработку вступления
                        await asyncio.sleep(1)
                        
                        # 3. Повторная попытка отправить комментарий
                        await post_to_send.answer_event(event, telegram_account.telegram_client, uniqalize_text=uniqalize_text)
                        telegram_account.log(f'({event.chat.title}) Успешно оставлен комментарий (попытка 2).')

                    except (UserAlreadyParticipantError, InviteRequestSentError):
                        # Если уже участник или отправлена заявка - ничего страшного, просто не спамим ошибками.
                        pass
                    except Exception as join_error:
                        # Если при вступлении произошла другая ошибка.
                        telegram_account.log_error(f"({event.chat.title}) Не удалось вступить в чат: {join_error.__class__.__name__}")
                
                # Обновляем счетчик только один раз после успешной отправки
                telegram_account.sent_messages_count += 1
                telegram_account.to_file()
                
            except (ChatWriteForbiddenError, ChannelPrivateError):
                chat_name = event.chat.title if event.chat else "неизвестный чат"
                telegram_account.log_warning(f'([{chat_name}]) Невозможно отправить сообщение. Комментарии отключены или это не пост.')
            except UserBannedInChannelError:
                chat_name = event.chat.title if event.chat else "неизвестный чат"
                telegram_account.log_warning(f'([{chat_name}]) Вы забанены в этом канале.')
            except FloodWaitError as fwe:
                chat_name = event.chat.title if event.chat else "неизвестный чат"
                telegram_account.log_warning(f'([{chat_name}]) Floodwait, сплю {fwe.seconds + 3} секунд.')
                await asyncio.sleep(fwe.seconds + 3)
            except SlowModeWaitError as smwe:
                chat_name = event.chat.title if event.chat else "неизвестный чат"
                telegram_account.log_warning(f'([{chat_name}]) Включен медленный режим, жду {smwe.seconds} секунд.')
                await asyncio.sleep(smwe.seconds)
            except Exception as e:
                chat_name = event.chat.title if event.chat else "неизвестный чат"
                telegram_account.log_error(f'Неизвестная ошибка при комментировании в {chat_name}: {e.__class__.__name__}')

        # Ставим флаг, чтобы не регистрировать обработчик повторно
        telegram_account._autocomments_handler_registered = True
        telegram_account.log_state('Модуль автокомментирования активен и ждет посты.')