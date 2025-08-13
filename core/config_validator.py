from __future__ import annotations
import json
from pathlib import Path
from typing import Tuple, List
def _expect_bool(d, key, errors, ctx):
    v=d.get(key); 
    if not isinstance(v, bool): errors.append(f"{ctx}.{key}: ожидается bool, получено {type(v).__name__}")
def _expect_list(d, key, errors, ctx):
    v=d.get(key);
    if not isinstance(v, list): errors.append(f"{ctx}.{key}: ожидается список")
def validate_config(path: str | Path) -> Tuple[bool, List[str]]:
    p=Path(path)
    if not p.exists():
        return False, [f"Файл конфига {p} не найден. Откройте настройки и сохраните их хотя бы один раз."]
    try: cfg=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        return False, [f"Не удалось прочитать JSON {p}: {e}"]
    errors: List[str]=[]
    prof=cfg.get('profile', {})
    if isinstance(prof, dict):
        _expect_bool(prof,'enabled',errors,'profile'); _expect_list(prof,'first_name',errors,'profile'); _expect_list(prof,'last_name',errors,'profile'); _expect_list(prof,'username',errors,'profile'); _expect_list(prof,'bio',errors,'profile')
    else: errors.append('profile: ожидается объект')
    ac=cfg.get('autocomments', {})
    if isinstance(ac, dict): _expect_bool(ac,'enabled',errors,'autocomments'); _expect_list(ac,'posts',errors,'autocomments')
    else: errors.append('autocomments: ожидается объект')
    ap=cfg.get('autoposts', {})
    if isinstance(ap, dict): _expect_bool(ap,'enabled',errors,'autoposts'); _expect_list(ap,'channels',errors,'autoposts')
    else: errors.append('autoposts: ожидается объект')
    aj=cfg.get('autojoin', {})
    if isinstance(aj, dict): _expect_bool(aj,'enabled',errors,'autojoin'); _expect_list(aj,'channels',errors,'autojoin')
    else: errors.append('autojoin: ожидается объект')
    return len(errors)==0, errors
