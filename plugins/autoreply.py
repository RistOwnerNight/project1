import sys
import traceback
from telethon import events
from telethon.tl.types import PeerUser
from core.account import TelegramAccount

class AutoReply:
    @staticmethod
    async def handle_new_messages(telegram_account: TelegramAccount, text: str):
        telegram_account.log_state('Автоответ запущен!')

        # Проверяем, был ли обработчик уже зарегистрирован
        if hasattr(telegram_account, '_autoreply_handler_registered') and telegram_account._autoreply_handler_registered:
            telegram_account.log_state('Обработчик автоответа уже активен.')
            return

        async def handle_new_message(event):
            # Реагируем только на входящие личные сообщения от пользователей (не ботов)
            if isinstance(event.message.peer_id, PeerUser) and not event.message.out:
                try:
                    from_user = await event.get_sender()
                    if from_user and not from_user.bot:
                        telegram_account.log(f"[Автоответ]: Отвечаю на '{event.message.raw_text[:20]}...'")
                        await event.respond(text)
                except Exception as e:
                    telegram_account.log_error(f"Ошибка в автоответчике: {e}")

        # Регистрируем обработчик
        telegram_account.telegram_client.add_event_handler(handle_new_message, events.NewMessage)
        
        # Ставим флаг, чтобы не регистрировать его повторно
        telegram_account._autoreply_handler_registered = True
        telegram_account.log_state('Обработчик автоответа успешно зарегистрирован.')
        
        # УБИРАЕМ ЦИКЛ ОЖИДАНИЯ ОТСЮДА
        # await telegram_account.telegram_client.run_until_disconnected() 