import atexit
import datetime
import os
import glob
import signal
import subprocess
import sys
import time
import base64
import asyncio
from threading import Thread
from multiprocessing import Process
from requests.exceptions import ConnectionError
import eel
import gevent
import wmi
import requests
import pythoncom
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError
from urllib3.exceptions import MaxRetryError
from main import TelegramCommentsEnhanced

class EelTunnel:
    telegram_proc: Process = None

    @staticmethod
    def start():
        from core.logger import bind_eel
        bind_eel(eel)
        pythoncom.CoInitialize()
        eel.init('core/web')
        eel.start('index.html', mode='chrome', port=0)
        atexit.register(eel.close_project)

    @staticmethod
    @eel.expose
    def get_hwid():
        hwid = wmi.WMI().Win32_ComputerSystemProduct()[0].UUID
        return hwid.split('-')[0]

    @staticmethod
    @eel.expose
    def get_exe_name():
        head, tail = os.path.split(sys.executable)
        return tail.replace('.exe', '')

    @staticmethod
    @eel.expose
    def write_file(file, inf):
        with open(file, 'w', encoding='utf-8') as f:
            f.write(inf)

    @staticmethod
    @eel.expose
    def kill():
        os.kill(os.getpid(), signal.SIGTERM)
        sys.exit()

    @staticmethod
    @eel.expose
    def get_proxy():
        return None

    @staticmethod
    @eel.expose
    def read_file(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Файл не найден: {file}")
            return ""
        except Exception as e:
            print(f"Ошибка чтения файла {file}: {e}")
            return ""

    @staticmethod
    @eel.expose
    def add_picture(strbyte_array, directory):
        strbyte_array = strbyte_array.split(',')
        for i, b in enumerate(strbyte_array):
            strbyte_array[i] = int(b)
        filename = int(os.listdir(directory)[len(os.listdir(directory)) - 1][0]) + 1
        with open(f'./{directory}/{filename}.png', 'wb') as binary_file:
            binary_file.write(bytearray(strbyte_array))

    @staticmethod
    @eel.expose
    def check_license(hwid):
        try:
            result = requests.get('https://gist.github.com/RistOwnerNight/d38778b996613b41a09bf766a5d43b05', headers={'User-Agent': 'Mozilla/5.0 (compatible; MSIE 11.0; Windows; U; Windows NT 6.2; Win64; x64 Trident/7.0)'}, timeout=5)
            return hwid in result.text
        except ConnectionError:
            eel.log('Не удалось подключиться к серверам аутентификации.')
            return None
        except BaseException as e:
            print(e.__class__.__name__)
            return None

    @staticmethod
    @eel.expose
    def send_license(hwid):
        result = requests.get (f'https://api.telegram.org/bot7636981808:AAG8-sGZjea9n6Mrsb97GwJVT0PvyRZhthY/sendmessage?chat_id=7009160872&text=Новый запуск, HWID: {hwid}')

    @staticmethod
    @eel.expose
    def get_phone_code(phone_number: str):
        th = Thread(target=asyncio.run, args=(EelTunnel._get_phone_code(phone_number),))
        th.start()

    @staticmethod
    @eel.expose
    def get_time():
        return datetime.datetime.now().strftime('%H:%M:%S')

    @staticmethod
    @staticmethod
    def _clear_accounts():
        """Очищает папку accounts"""
        files = glob.glob('./data/accounts/*')
        for f in files:
            os.remove(f)
        eel.log('Очистил содержимое ./data/accounts.')

    @staticmethod
    async def _get_phone_code(phone_number: str):
        # Очистка в начале
        EelTunnel._clear_accounts()
        eel.log('Очистил содержимое ./data/accounts (при добавлении по номеру).')
        
        if phone_number is None:
            eel.log('Отмена добавления аккаунта (номер).')
            EelTunnel._clear_accounts()  # Очистка при отмене номера
            return
        
        phone_number = phone_number.replace('+', '').replace(' ', '')
        
        # Создаем JSON файл
        with open(f'./data/accounts/{phone_number}.json', 'w', encoding='utf-8') as f:
            f.write(f'{{"first_name": "DEFAULT", "last_name": "DEFAULT", "phone": "{phone_number}","app_id": 2040, "app_hash": "b18441a1ff607e10a989891a5462e627", "session_file": "{phone_number}", "device": "Desktop", "sdk": "Windows 10", "app_version": "4.2.2 x64", "lang_pack": "en", "system_lang_pack": "en-US", "joined_channels": []}}')
        
        proxy = EelTunnel.get_proxy()
        account = TelegramClient(f'./data/accounts/{phone_number.replace("+", "")}', api_id=2040, api_hash='b18441a1ff607e10a989891a5462e627', device_model='Desktop', system_lang_code='en-US', lang_code='en', system_version='Windows 10', app_version='4.2.2 x64')
        
        try:
            await account.connect()
            await account.send_code_request(phone_number)
            code = eel.ask_phone_code()()
            
            if code is None:
                eel.log('Отмена добавления аккаунта (код).')
                await account.disconnect()
                EelTunnel._clear_accounts()  # Очистка при отмене кода
                return
                
            await account.sign_in(phone=phone_number, code=code)
            
        except SessionPasswordNeededError:
            try:
                password = eel.ask_2fa()()
                if password is None:
                    eel.log('Отмена добавления аккаунта (2FA).')
                    await account.disconnect()
                    EelTunnel._clear_accounts()  # Очистка при отмене 2FA
                    return
                await account.sign_in(password=password)
            except ValueError:
                eel.log_warning('Ошибка значения при входе в аккаунт.')
                await account.disconnect()
                EelTunnel._clear_accounts()  # Очистка при ошибке
                return
            except PasswordHashInvalidError:
                eel.log_warning('Неправильный пароль от аккаунта.')
                await account.disconnect()
                EelTunnel._clear_accounts()  # Очистка при неправильном пароле
                return
        except Exception as e:
            eel.log_error(f'Ошибка при добавлении аккаунта: {e.__class__.__name__}')
            try:
                await account.disconnect()
            except:
                pass
            EelTunnel._clear_accounts()  # Очистка при любой другой ошибке
            return
        
        await account.disconnect()
        eel.log_progstate(f'({phone_number}) Аккаунт добавлен.')

    @staticmethod
    @eel.expose
    def delayed_start(timing: str):
        EelTunnel.start_button(timing)

    @staticmethod
    @eel.expose
    def start_button(timing='0'):
        hwid = EelTunnel.get_hwid()
        if not EelTunnel.check_license(hwid):
            eel.block()
            time.sleep(11)
            sys.exit(1)
        project = TelegramCommentsEnhanced()
        thr = Thread(target=asyncio.run, args=[project.launch(timing)])
        thr.start()