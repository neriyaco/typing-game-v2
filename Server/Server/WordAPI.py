from urllib.request import urlopen
from json import loads, dumps
import time
from pprint import pprint

RANDOM_WORD_URL = "https://random-word-api.herokuapp.com/word?number={0}"


def get_words(number_of_words: int = 1):
    response = urlopen(RANDOM_WORD_URL.format(number_of_words)).read()
    return loads(response.decode())


def _test(start: int = 0, end: int = 10, step: int = 1):
    for i in range(start, end, step):
        words = get_words(i)
        if len(words) != i:
            return False
    return True


if __name__ == '__main__':
    if not _test():
        raise Exception("WordAPI is broken")
    else:
        print("Test passed successfully")
