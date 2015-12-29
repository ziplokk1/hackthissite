import hashlib
import logging
import re
from functools import wraps

import requests
from itertools import permutations
from StringIO import StringIO
from zipfile import ZipFile

from BeautifulSoup import BeautifulSoup
from PIL import Image
from collections import Counter

import creds

session = requests.Session()


def login(username, password):
    """
    Login to hackthissite.org
    :param username: Your username
    :param password: Your password
    :return:
    """
    logging.info('logging in')
    r = session.post('https://www.hackthissite.org/user/login',
                     data={'username': username, 'password': password, 'btn_submit': 'Login'},
                     headers={'Referer': 'https://www.hackthissite.org/'})
    logging.info('logged in')
    return r


def parse_response(f):
    @wraps(f)
    def inner(*args, **kwargs):
        resp = f(*args, **kwargs)
        soup = BeautifulSoup(resp.content)
        data = soup.find('td', {'class': 'sitebuffer'}).find('center').find('div', {'class': 'light-td'}).text.strip()
        print 'Submitted Answer Response:', data
        return resp
    return inner


class Prog(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)


class Prog1(Prog):
    """
    Solver for https://www.hackthissite.org/missions/prog/1/
    """

    def get_wordlist(self):
        """
        Download the zipfile which contains and read the wordlist file contained within
        :return: list containing words
        """
        self.logger.info('fetching wordlist.txt')
        zip_response = session.get('https://www.hackthissite.org/missions/prog/1/wordlist.zip')
        zipdata = StringIO()
        zipdata.write(zip_response.content)
        fl = ZipFile(zipdata)
        words = fl.open('wordlist.txt')
        self.logger.info('fetched wordlist.txt')
        return [x.strip() for x in words.readlines()]

    def scrambled_words(self):
        """
        Scrape the scrambled words list from the site
        :return: list containing scrambled words
        """
        url = 'https://www.hackthissite.org/missions/prog/1/'
        self.logger.info('fetching %s' % url)
        page = session.get(url)
        soup = BeautifulSoup(page.content)
        self.logger.info('parsing scrambled words')
        l = soup.find('li', text=re.compile('List of scrambled words'))
        words = l.parent.parent.parent.findAll('li')
        b = [x.text.strip() for x in words]
        self.logger.info('words found: %s' % b)
        return b

    def solve(self):
        """
        Check each permutation of each word in the scrambled words list and compare them to
          the wordslist.txt contents.
        :return: List containing unscrambled words
        """
        wordlist = self.get_wordlist()
        scrambled_words = self.scrambled_words()
        solved = []
        self.logger.info('calculating permutations')
        for word in scrambled_words:
            self.logger.debug('calculating permutations for %s' % word)
            for permutation in permutations(word):
                perm = ''.join(permutation)
                if perm in wordlist:
                    solved.append(perm)
                    self.logger.debug('valid permutation found: %s' % perm)
                    break
            else:
                self.logger.debug('moving to next word')
                continue
        self.logger.info('permutations complete: %s' % solved)
        return solved

    def submit_answer(self, answerlist):
        """
        Post the answer to the site
        :param answerlist: List of unscrambled words
        :return:
        """
        self.logger.info('submitting answer')
        return session.post('https://www.hackthissite.org/missions/prog/1/index.php',
                            data={'solution': ','.join(answerlist), 'submitbutton': 'ayy'},
                            headers={'Referer': 'https://www.hackthissite.org/missions/prog/1/'})

    @parse_response
    def start(self):
        answers = self.solve()
        r = self.submit_answer(answers)
        return r


class Prog2(Prog):
    """
    Solver for https://www.hackthissite.org/missions/prog/2/
    """

    char_morse_dict = {
        'A': '.-', 'B': '-...', 'C': '-.-.', 'D': '-..', 'E': '.', 'F': '..-.',
        'G': '--.', 'H': '....', 'I': '..', 'J': '.---', 'K': '-.-', 'L': '.-..',
        'M': '--', 'N': '-.', 'O': '---', 'P': '.--.', 'Q': '--.-', 'R': '.-.',
        'S': '...', 'T': '-', 'U': '..-', 'V': '...-', 'W': '.--', 'X': '-..-',
        'Y': '-.--', 'Z': '--..', '0': '-----', '1': '.----', '2': '..---', '3': '...--',
        '4': '....-', '5': '.....', '6': '-....', '7': '--...', '8': '---..', '9': '----.',
        '.': '.-.-.-', ',': '--..--', '?': '..--..', "'": '.----.', '/': '-..-.', '(': '-.--.-',
        ')': '-.--.-', ':': '---...', ';': '-.-.-.', '=': '-...-', '+': '.-.-.', '-': '-....-',
        '_': '..--.-', '"': '.-..-.', '$': '...-..-', '': ''
    }

    # inverse keys/values so that we can get the char associated with the morse
    morse = {v: k for k, v in char_morse_dict.items()}

    def __init__(self):
        Prog.__init__(self)
        # Request needed to be able to see/download the image
        self.page = session.get('https://www.hackthissite.org/missions/prog/2/')

    def get_image(self):
        """
        Download the image on the page.

        While this could be parsed, the image location is always the same, so
        it's easier to just get the url rather than parse the page and get the
        img src.
        :return:
        """
        response = session.get('https://www.hackthissite.org/missions/prog/2/PNG/',
                               headers={
                                   'Host': 'www.hackthissite.org',
                                   'Upgrade-Insecure-Requests': 1
                               })
        image = Image.open(StringIO(response.content))
        # image = Image.open('download.png')
        return image

    def analyze(self, image):
        """
        Calculate the distance between each white pixel and return a list
        of distances between each point.

        :param image: PIL Image object of the image provided by hackthissite
        :return: List containing distances between each white pixel
        """
        self.logger.debug('analyzing image')
        data = list(image.getdata())
        solution = []
        last_white = None
        for idx, i in enumerate(data):
            if i:
                if last_white:
                    self.logger.debug('index=%d last_white=%d' % (idx, last_white))
                    solution.append(idx - last_white)
                else:
                    solution.append(idx)
                last_white = idx
        self.logger.debug('analysis complete: %s' % solution)
        return solution

    def solve(self, analysislist):
        """
        Turn the list from analyze into a string object.
        :param analysislist:
        :return:
        """
        # convert ints to morse sequence separated by space
        answer = ''.join(map(lambda x: str(unichr(x)), analysislist))
        # convert morse to characters
        answer = ''.join(map(lambda x: self.morse[x], answer.split()))
        self.logger.info('answer: %s' % answer)
        return answer

    def submit_answer(self, answer):
        self.logger.info('submitting answer')
        return session.post('https://www.hackthissite.org/missions/prog/2/index.php',
                            data={'solution': answer, 'submitbutton': 'lmao'},
                            headers={'Referer': 'https://www.hackthissite.org/missions/prog/2/'})

    @parse_response
    def start(self):
        img = self.get_image()
        solution = self.analyze(img)
        answer = self.solve(solution)
        r = self.submit_answer(answer)
        return r


class Prog3(Prog):

    def eval_cross_total(self, strmd5):
        int_total = 0
        # this line is unnecessary since python strings are already iterable
        # but this is just to show what it does
        arr_md5_chars = list(strmd5)
        for value in arr_md5_chars:
            int_total += int('0x0' + value, 0)
        return int_total

    def encrypt_string(self, strst, strpw):
        # strst is the content of the entire file with serials
        str_password_md5 = hashlib.md5(strpw).hexdigest()
        int_md5_total = self.eval_cross_total(str_password_md5)
        arr_encrypted_values = []
        int_str_len = len(strst)
        for i in range(int_str_len):
            ordinal = ord(strst[i:i+1])
            pw = '0x0' + str_password_md5[i % 32:i % 32+1]
            arr_encrypted_values.append(ordinal + int(pw, 0) - int_md5_total)
            int_md5_total = self.eval_cross_total(hashlib.md5(strst[0:i+1]).hexdigest()[0:16] + hashlib.md5(str(int_md5_total)).hexdigest()[0:16])
        print arr_encrypted_values
        return ' '.join([str(x) for x in arr_encrypted_values])


if __name__ == '__main__':
    logging.basicConfig(level=20)
    # login(creds.username, creds.password)
    #
    # p1 = Prog1()
    # p1.start()
    #
    # p2 = Prog2()
    # p2.start()

    p3 = Prog3()
    print hashlib.md5('ayylmao').hexdigest()
    data = p3.encrypt_string("""99Z-KH5-OEM-240-1.1
QGG-V33-OEM-0B1-1.1
Z93-Z29-OEM-BNX-1.1
IQ0-PZI-OEM-PK0-1.1
UM4-VDL-OEM-B9O-1.1
L0S-4R2-OEM-UQL-1.1
JBL-EYQ-OEM-ABB-1.1
NL1-3V3-OEM-L4C-1.1
7CQ-1ZR-OEM-U3I-1.1
XX0-IHL-OEM-5XK-1.1
KJQ-RXG-OEM-TW8-1.1
OZR-LW1-OEM-5EM-1.1
0B8-6K5-OEM-EFN-1.1
OE2-20L-OEM-SSI-1.1
0ME-HAE-OEM-9XB-1.1
""", 'ayylmao')
    ctr = Counter(data.split())
    print ctr