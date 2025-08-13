import re
import random

class Uniqalize:
    __module__ = __name__
    __qualname__ = "Uniqalize"
    __firstlineno__ = 5
    uniq_dict = {
        "А": "A",
        "а": "aᴀ",
        "В": "B",
        "в": "ʙ",
        "с": "cᴄ",
        "Е": "E",
        "е": "eᴇ",
        "К": "K",
        "к": "ᴋ",
        "м": "ᴍ",
        "Н": "H",
        "н": "ʜ",
        "О": "O",
        "о": "oᴏ",
        "Р": "P",
        "р": "pᴘ",
        "С": "C",
        **{
            'с': 'c',
            'Т': 'Tᴛ',
            'у': 'y',
            'Х': 'X',
            'х': 'xx'
        }
    }

    @classmethod
    def uniqalize_string(cls, _string: str) -> str:
        if _string is None:
            return None

        _string_list = list(_string)

        for i, symbol in enumerate(_string_list):
            if random.random() < 0.6:  # 60% chance to skip
                continue
            

            replacement_options = cls.uniq_dict.get(symbol, symbol)

            _string_list[i] = random.choice(replacement_options)

        return "".join(_string_list)

    @classmethod
    def randomize_brackets(cls, _string: str) -> str:

        if _string is None:
            return None


        strs_to_process = re.findall(r"\{.*?\}", _string)

        for s in strs_to_process:

            substr = s.replace("{", "").replace("}", "")
            substr_options = substr.split("|")

            if len(substr_options) == 1:
                chosen_substr = substr_options[0]
            else:

                chosen_substr = random.choice(substr_options)

            _string = _string.replace(s, chosen_substr, 1)

        return _string

    __static_attributes__ = ()