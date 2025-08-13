import asyncio
import random
from typing import Union, List
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest, SetPrivacyRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.errors import AboutTooLongError, FirstNameInvalidError, UserDeactivatedBanError, UsernameInvalidError, AuthKeyUnregisteredError, UsernameOccupiedError, UsernameNotModifiedError, FloodWaitError, SessionRevokedError
from telethon.tl.types import InputPrivacyKeyProfilePhoto, InputPrivacyValueAllowAll, InputPhoto
from telethon import TelegramClient
from core.account import TelegramAccount
from plugins.randomize_str import RandomizeStr
from telethon import functions, types

class AutoProfile:
    @staticmethod
    async def keep_settings(telegram_account: TelegramAccount, first_name, last_name, avatar_path):
        return None

    @staticmethod
    async def update_info(telegram_account: TelegramAccount, first_name: Union[str, List[str], type(None)]=None, last_name: Union[str, List[str], type(None)]=None, bio: Union[str, List[str], type(None)]=None, username: Union[str, List[str], type(None)]=None, photo: Union[str, List[str], type(None)]=None, should_hide_photo: bool=True):
        telegram_account.log_state('Меняю профиль!')
        if first_name is not None or last_name is not None or bio is not None:
            telegram_account.first_name = first_name = first_name if not isinstance(first_name, list) else random.choice(first_name)
            telegram_account.last_name = last_name = last_name if not isinstance(last_name, list) else random.choice(last_name)
            bio = bio if not isinstance(bio, list) else random.choice(bio)
            if '%link%' in bio:
                with open('./data/linkbot.txt', 'r', encoding='utf-8') as linkbot_file:
                    telegram_account.log('Получаю ссылку %link%.')
                    linkbot_text = linkbot_file.read().replace('\n', '')
                    linkbot_credentials = linkbot_text.split('::')
                    linkbot_token = linkbot_credentials[0]
                    linkbot_entity = linkbot_credentials[1]
                    bot = TelegramClient('./data/linkbot', api_id=2040, api_hash='b18441a1ff607e10a989891a5462e627')
                    await bot.connect()
                    if not await bot.is_user_authorized():
                        await bot.sign_in(bot_token=linkbot_token)
                    chat_invite = await bot(functions.messages.ExportChatInviteRequest(peer=int(linkbot_entity), request_needed=True))
                    await bot.disconnect()
                    bio = bio.replace('%link%', chat_invite.link)
            try:
                await telegram_account.telegram_client(UpdateProfileRequest(first_name, last_name, bio))
                telegram_account.log(f'Основные данные изменены. ({first_name} {last_name}, {bio}).')
            except FirstNameInvalidError:
                telegram_account.log_warning(f'Недопустимое имя. ({first_name[:10]}..)')
        if username is not None:
            for i in range(2):
                _username = username if not isinstance(username, list) else random.choice(username)
                _username = RandomizeStr.randomise_string(_username, '%')
                try:
                    telegram_account.log('Меняю имя пользователя.')
                    await telegram_account.telegram_client(UpdateUsernameRequest(_username))
                    telegram_account.log(f'Юзернейм изменён на {_username}.')
                    break
                except UsernameOccupiedError:
                    telegram_account.log_warning(f'Имя пользователя уже занято. ({_username})')
                except UsernameNotModifiedError:
                    telegram_account.log_warning(f'Имя пользователя не отличается от текущего имени пользователя. ({_username})')
                except UsernameInvalidError:
                    telegram_account.log_warning(f'Зарезервировано или неприемлемо. ({_username})')
                    continue
                except FloodWaitError as fw:
                    telegram_account.log_warning(f'Сплю {fw.seconds} секунд из-за ошибки Floodwait.')
                    try:
                        await telegram_account.telegram_client(UpdateUsernameRequest(_username))
                        telegram_account.log(f'Юзернейм изменён на {_username}.')
                        break
                    except UsernameOccupiedError:
                        telegram_account.log_warning(f'Имя пользователя уже занято. ({_username})')
                        continue
                    except UsernameNotModifiedError:
                        telegram_account.log_warning(f'Имя пользователя не отличается от текущего имени пользователя. ({_username})')
                        continue
                    except UsernameInvalidError:
                        telegram_account.log_warning(f'Зарезервировано или данное имя пользователя неприемлемо. ({_username})')
                        continue
                    except FloodWaitError as fw:
                        telegram_account.log_warning('Ошибка циклического Floodwait.')
                        continue
        if photo is not None:
            photo = photo if not isinstance(photo, list) else random.choice(photo)
            if should_hide_photo:
                # Очистка всех существующих фотографий профиля перед установкой новой
                try:
                    telegram_account.log('Удаляю все старые фотографии профиля.')
                    photos = await telegram_account.telegram_client.get_profile_photos('me')
                    if photos:
                        # Преобразуем фотографии в InputPhoto для DeletePhotosRequest
                        input_photos = [InputPhoto(id=photo.id, access_hash=photo.access_hash, file_reference=photo.file_reference) for photo in photos]
                        await telegram_account.telegram_client(DeletePhotosRequest(input_photos))
                        telegram_account.log(f'Удалено {len(photos)} старых фотографий профиля.')
                    else:
                        telegram_account.log('Старые фотографии профиля отсутствуют.')
                except Exception as e:
                    telegram_account.log_warning(f'Ошибка при удалении старых фото: {e.__class__.__name__}')
                
                # Установка нового фото
                telegram_account.log('Меняю фото профиля.')
                await telegram_account.telegram_client(UploadProfilePhotoRequest(fallback=True, file=await telegram_account.telegram_client.upload_file(photo)))
                telegram_account.log(f'Фото изменено на: {photo}.')
            telegram_account.log('Создаю поток, смотрящий за основными данными аккаунта.')
            asyncio.get_event_loop().create_task(AutoProfile.keep_settings(telegram_account, first_name, last_name, photo))
        telegram_account.to_file()