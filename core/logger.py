import logging, sys

_eel = None

def _ensure_logging():
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            stream=sys.stdout
        )

def bind_eel(eel_module):
    global _eel
    _eel = eel_module

def _to_text(x):
    if isinstance(x, bytes):
        for enc in ('utf-8', 'cp1251', 'latin-1'):
            try:
                return x.decode(enc)
            except Exception:
                pass
        return x.decode('utf-8', errors='replace')
    return str(x)

def _send_to_ui(level, msg, phone=None):
    if _eel is None:
        return
    txt = _to_text(msg)
    try:
        if level >= logging.ERROR:
            try:
                _eel.log_error(txt, phone) if phone else _eel.log_error(txt)
            except TypeError:
                _eel.log_error(txt)
        elif level >= logging.WARNING:
            try:
                _eel.log_warning(txt, phone) if phone else _eel.log_warning(txt)
            except TypeError:
                _eel.log_warning(txt)
        else:
            try:
                _eel.log(txt, phone) if phone else _eel.log(txt)
            except TypeError:
                _eel.log(txt)
    except Exception:
        pass

def info(msg, phone=None):
    _ensure_logging()
    logging.info(_to_text(msg))
    _send_to_ui(logging.INFO, msg, phone)

def warn(msg, phone=None):
    _ensure_logging()
    logging.warning(_to_text(msg))
    _send_to_ui(logging.WARNING, msg, phone)

def error(msg, phone=None):
    _ensure_logging()
    logging.error(_to_text(msg))
    _send_to_ui(logging.ERROR, msg, phone)

log = info
