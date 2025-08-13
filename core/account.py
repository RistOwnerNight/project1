# core/account.py
import asyncio, datetime, json, random, threading
from asyncio import sleep
from types import NoneType
from pathlib import Path

import eel
from telethon import TelegramClient
from telethon.errors import (
    BadRequestError, ChannelInvalidError, ChannelPrivateError, ChannelsTooMuchError,
    FloodWaitError, InviteHashEmptyError, InviteHashExpiredError, InviteHashInvalidError,
    InviteRequestSentError, UserAlreadyParticipantError, UsernameInvalidError,
)
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.chatlists import (
    CheckChatlistInviteRequest, JoinChatlistInviteRequest, LeaveChatlistRequest,
)
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.functions.messages import (
    GetDialogFiltersRequest, ImportChatInviteRequest, StartBotRequest, UpdateDialogFilterRequest,
)
from telethon.tl.types import (
    Channel, InputPeerChat, InputPeerChannel, InputPeerNotifySettings, InputPeerUser,
    NotificationSoundDefault, PeerChat, PeerChannel, PeerUser, TextWithEntities,
    UpdateDialogFilter, InputChatlistDialogFilter, DialogFilter,
)
from telethon.tl.types.chatlists import ChatlistInvite, ChatlistInviteAlready
from telethon.tl.types.messages import DialogFilters

# все ошибки «не получилось присоединиться»
ERR_JOIN = (
    ChannelInvalidError, UsernameInvalidError, ChannelPrivateError,
    InviteHashExpiredError, InviteRequestSentError, InviteHashEmptyError,
    InviteHashInvalidError, UserAlreadyParticipantError,
)

# ───────────────────────── helpers ──────────────────────────
_plain = lambda v: v.text if isinstance(v, TextWithEntities) else (
    v if isinstance(v, str) else "Без названия" if v is None else str(v)
)

def _proxy_from_file() -> dict | None:
    return None

def get_config_setting(key, default=False):
    """Получает настройку из конфига"""
    try:
        config_path = Path("./data/config.json")
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # Поддержка вложенных ключей
            if key == 'delete_folders' and 'autojoin' in config:
                return config['autojoin'].get('delete_folders', default)
    except Exception as e:
        print(f"Ошибка чтения конфига: {e}")
    return default

# ───────────────────── основной класс ──────────────────────
class TelegramAccount:
    def __init__(
        self, first_name, last_name, phone, app_id, app_hash, session_file,
        device, sdk, app_version, lang_pack, system_lang_pack,
        last_joined_channel, linked_channel_id=None, joined_channels=None, sent_messages_count=0,
    ):
        self.first_name, self.last_name, self.phone = first_name, last_name, phone
        self.app_id, self.app_hash, self.session_file = app_id, app_hash, session_file
        self.device, self.sdk, self.app_version = device, sdk, app_version
        self.lang_pack, self.system_lang_pack = lang_pack, system_lang_pack
        self.last_joined_channel, self.linked_channel_id = last_joined_channel, linked_channel_id
        self.joined_channels = joined_channels if joined_channels is not None else []
        self.sent_messages_count = sent_messages_count
        self.telegram_client = TelegramClient(
            f"./data/accounts/{self.session_file}",
            api_id=2040, api_hash="b18441a1ff607e10a989891a5462e627")
        self._folders_cleaned = False  # Флаг для однократной очистки

    # ────────────── фабрика из json ─────────────
    @staticmethod
    def from_file(path: str):
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        acc = TelegramAccount(**{
            **{k: d.get(k) for k in (
                "first_name", "last_name", "phone", "app_id", "app_hash",
                "session_file", "device", "sdk", "app_version", "lang_pack",
                "system_lang_pack", "last_joined_channel")},
            "linked_channel_id": d.get("linked_channel_id"),
            "joined_channels": d.get("joined_channels"),
            "sent_messages_count": d.get("sent_messages_count", 0),
        })
        acc.log(f"Аккаунт {acc.first_name} {acc.last_name} загружен.")
        return acc

    # ──────────── универсальный вывод ───────────
    def _log(self, msg, kind="log"):
        if kind not in ("log", "log_warning", "log_error"):
            kind = "log"
        getattr(eel, kind)(msg, self.phone)

    # ── методы-обёртки для совместимости ──
    def log(self, msg):              self._log(msg, "log")
    def log_warning(self, msg):      self._log(msg, "log_warning")
    def log_error(self, msg):        self._log(msg, "log_error")
    def log_state(self, msg):        eel.log_progstate(msg, self.phone)

    # ────────────────────────────────────────────
    def to_file(self):
        d = self.__dict__.copy(); d.pop("telegram_client", None); d.pop("_folders_cleaned", None)
        Path(f"./data/accounts/{self.session_file}.json").write_text(json.dumps(d), encoding="utf-8")

    # ───────────── очистка пользовательских папок при запуске ─────────────
    async def _initial_cleanup_folders(self):
        # Проверяем настройку перед выполнением
        if not get_config_setting('delete_folders', False):
            return
            
        if self._folders_cleaned:
            return
            
        try:
            # Получаем все папки
            df_resp = await self.telegram_client(GetDialogFiltersRequest())
            filters = df_resp.filters if isinstance(df_resp, DialogFilters) else df_resp
            
            # Фильтруем только пользовательские папки (ID > 1, исключаем архив и другие системные)
            all_folders = [f for f in filters if isinstance(f, DialogFilter) and getattr(f, 'id', 0) > 0]
            
            folder_count = len(all_folders)
            self.log(f"Найдено папок: {folder_count}")
            
            # Удаляем все пользовательские папки
            if folder_count > 0:
                self.log_warning(f"Удаляю {folder_count} папок при запуске.")
                
                for folder in all_folders:
                    try:
                        folder_name = _plain(getattr(folder, 'title', 'Неизвестная папка'))
                        folder_id = getattr(folder, 'id', 0)
                        
                        # Удаляем папку
                        await self.telegram_client(UpdateDialogFilterRequest(
                            id=folder.id,
                            filter=None  # None означает удаление папки
                        ))
                        
                        self.log(f"папка '{folder_name}' удалена.")
                        await sleep(0.5)  # Небольшая задержка между удалениями
                        
                    except Exception as e:
                        self.log_error(f"Ошибка при удалении папки '{folder_name}': {e}")
                
                self.log(f"Очистка папок завершена. Удалено {folder_count} папок.")
            else:
                self.log("Папки отсутствуют.")
            
            self._folders_cleaned = True
                
        except Exception as e:
            self.log_error(f"Ошибка при очистке папок: {e}")

    # ───────────────── мониторинг ─────────────────
    async def check_account_info(self):
        # Очищаем папки только один раз при самом первом запуске
        await self._initial_cleanup_folders()
        asyncio.create_task(self._check_loop())

    async def _check_loop(self):
        while True:
            dialogs = await self.telegram_client.get_dialogs()
            if not dialogs:
                eel.refresh_title(0, 0, 0, self.sent_messages_count, 0)
                await sleep(10)
                continue
            opened = sum(1 for d in dialogs if isinstance(d.entity, Channel) and (d.entity.username or d.entity.usernames))
            closed = sum(1 for d in dialogs if isinstance(d.entity, Channel)) - opened
            age = (datetime.datetime.now(datetime.timezone.utc) - dialogs[-1].date).days
            code = next(
                ("".join(filter(str.isdigit, d.message.raw_text))
                 for d in dialogs if d.id == 777000
                 and (datetime.datetime.utcnow() - d.message.date.replace(tzinfo=None)).total_seconds() <= 60
                 and len("".join(filter(str.isdigit, d.message.raw_text))) == 5),
                0
            )
            eel.refresh_title(opened, closed, age, self.sent_messages_count, code)
            await sleep(10)

    # ───────────────── участие ──────────────────
    async def participate(self, joinable, should_hide=False, min_delay=90, max_delay=110):        
        if self.last_joined_channel and isinstance(joinable, list) and self.last_joined_channel in joinable:
            joinable = joinable[joinable.index(self.last_joined_channel) + 1:]
        if not isinstance(joinable, list):
            joinable = [joinable]

        for item in joinable:
            is_last = item is joinable[-1]
            try:
                await self._handle_join(item, should_hide, 0 if is_last else min_delay, 0 if is_last else max_delay)
            except ChannelsTooMuchError:
                self.log_warning("Превышен лимит каналов."); return
            except ValueError:
                self.log_warning(f"[{item}] Ошибка значения.")
            if not is_last and (min_delay or max_delay):
                delay = min_delay if min_delay == max_delay else random.randint(min_delay, max_delay)
                self.log(f"Жду {delay} сек перед следующим каналом.")
                await asyncio.sleep(delay)

    # ───────────── низкоуровневое присоединение ─────────────
    async def _handle_join(self, target, should_hide, min_d, max_d):
        if not isinstance(target, int):
            self.last_joined_channel = target; self.to_file()

        join_ids = await (
            self._join_channel(target) if isinstance(target, int) else
            self._join_channel_list(target) if "addlist" in str(target) else
            self._send_join_channel_request(target) if any(x in str(target) for x in ("+", "joinchat")) else
            self._join_channel(target)
        )
        join_ids = [join_ids] if not isinstance(join_ids, list) else join_ids

        for cid in filter(None, join_ids):
            self.save_channel_as_joined(cid)
            if should_hide and len(join_ids) <= 10:
                try:
                    ent = await self.telegram_client.get_entity(cid)
                    await self.disable_channel_notifications(ent)
                    await self.add_channel_to_archive(ent)
                except ChannelPrivateError:
                    pass

        if min_d or max_d:
            delay = min_d if min_d == max_d else random.randrange(min_d, max_d)
            # Убрал вывод "Сплю X сек." для addlist ссылок
            if "addlist" not in str(target):
                self.log(f"[{target}] Сплю {delay} сек.")
            await sleep(delay)

    # ───────── одиночный канал ─────────
    async def _join_channel(self, link_or_id):
        try:
            ent = await self.telegram_client.get_input_entity(link_or_id)
            upd = await self.telegram_client(JoinChannelRequest(ent))
            self.log(f"[{link_or_id}]({_plain(upd.chats[0].title)}) Присоединился.")
            return upd.chats[0].id
        except ERR_JOIN as e:
            self.log_warning(f"[{link_or_id}] {e.__class__.__name__}.")
        return None

    # ───────── invite-ссылка ─────────
    async def _send_join_channel_request(self, link):
        h = link.translate({ord(c): None for c in "https:/t.me+joinchat"})
        try:
            upd = await self.telegram_client(ImportChatInviteRequest(h))
            self.log(f"[{link}]({_plain(upd.chats[0].title)}) Присоединился.")
            return upd.chats[0].id
        except ERR_JOIN as e:
            self.log_warning(f"[{link}] {e.__class__.__name__}.")
        return None

    # ──────────────── addlist ────────────────
    async def _join_channel_list(self, link):
        slug = ("https://" + link if link.startswith("t.me") else link).split("/")[-1]
        try:
            inv = await self.telegram_client(CheckChatlistInviteRequest(slug=slug))

            # имя папки
            if isinstance(inv, ChatlistInvite):
                title = _plain(inv.title)
            else:
                df_resp = await self.telegram_client(GetDialogFiltersRequest())
                filters = df_resp.filters if isinstance(df_resp, DialogFilters) else df_resp
                title = next((_plain(f.title) for f in filters if getattr(f, "id", None) == inv.filter_id), "Неизвестная папка")

            # уже в папке
            if isinstance(inv, ChatlistInviteAlready):
                # Изменил формат вывода - убрал ссылку, оставил только название папки
                self.log(f"{title} Присоединился к списку каналов.")
                joined = [c.id for c in inv.chats if isinstance(c, Channel)]

                if inv.missing_peers:
                    peers = []
                    for p in inv.missing_peers:
                        try:
                            e = await self.telegram_client.get_entity(p)
                            peers.append(
                                InputPeerChannel(p.channel_id, e.access_hash) if isinstance(p, PeerChannel) else
                                InputPeerChat(p.chat_id)                      if isinstance(p, PeerChat)   else
                                InputPeerUser(p.user_id, e.access_hash)
                            )
                        except Exception: pass
                    if peers:
                        ups = await self.telegram_client(JoinChatlistInviteRequest(slug=slug, peers=peers))
                        joined.extend(u.channel_id for u in ups.updates if hasattr(u, "channel_id"))
                return joined

            # новое приглашение
            if isinstance(inv, ChatlistInvite):
                ups = await self.telegram_client(JoinChatlistInviteRequest(slug=slug, peers=inv.peers))
                flt_id = next(u.filter.id for u in ups.updates if isinstance(u, UpdateDialogFilter))
                await self.telegram_client(LeaveChatlistRequest(
                    chatlist=InputChatlistDialogFilter(filter_id=flt_id), peers=[]
                ))
                # Изменил формат вывода - убрал ссылку, оставил только название папки
                self.log(f"{title} Присоединился к списку каналов.")
                return [p.channel_id for p in inv.peers if hasattr(p, "channel_id")]

            self.log_warning(f"[{link}] Неизвестное приглашение.")
        except BadRequestError as bre:
            if bre.message in ("CHATLISTS_TOO_MUCH", "INVITE_SLUG_EXPIRED"):
                self.log_warning(f"[{link}] {bre.message}."); return None
            raise
        except Exception as e:
            self.log_error(f"[{link}] Ошибка addlist: {e}")
        return []

    # ────────────── утилиты ─────────────
    async def add_channel_to_archive(self, ent):
        await self.telegram_client.edit_folder(ent, 1)
        self.log(f"({_plain(ent.title)}) Добавлено в архив.")

    async def disable_channel_notifications(self, ent):
        await self.telegram_client(UpdateNotifySettingsRequest(
            peer=ent,
            settings=InputPeerNotifySettings(
                show_previews=False, mute_until=datetime.datetime.now() + datetime.timedelta(days=365),
                sound=NotificationSoundDefault())
        ))
        self.log(f"({_plain(ent.title)}) Уведомления выключены.")

    def save_channel_as_joined(self, cid):
        self.joined_channels.append(cid); self.to_file()

    async def remove_spamblock(self):
        self.log_warning("Снимаю спамблок.")
        await self.telegram_client(UnblockRequest("SpamBot"))
        await self.telegram_client(StartBotRequest(
            bot="SpamBot", peer=await self.telegram_client.get_me(), start_param="123"
        ))