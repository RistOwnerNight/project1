
import random
import string

class RandomizeStr:

    @staticmethod
    def randomise_string(_string: str, symbol: str):
        for s in _string:
            if not s == symbol:
                continue
            _string = _string.replace(s, random.choice(string.ascii_lowercase), 1)
            pass
        return _string