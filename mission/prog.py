import logging
import re
import requests
from itertools import permutations
from StringIO import StringIO
from zipfile import ZipFile

from BeautifulSoup import BeautifulSoup

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


class Prog1(object):
    """
    Solver for https://www.hackthissite.org/missions/prog/1/
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

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
                            data={'solution': ','.join(answerlist)},
                            headers={'Referer': 'https://www.hackthissite.org/missions/prog/1/'})

    def start(self):
        answers = self.solve()
        self.submit_answer(answers)
        print 'Done'


if __name__ == '__main__':
    logging.basicConfig(level=20)
    login(creds.username, creds.password)

    p1 = Prog1()
    p1.start()
