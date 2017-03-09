# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

from datetime import datetime, timedelta

import json
import logging
import os
import random
import time

import requests
import spacy
from spacy.symbols import dobj, nsubj, det
import tracery
from tracery.modifiers import base_english
import tweepy

from secret import *

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

DATE_FORMAT = '%Y-%m-%d'
START_DATE = '2017-03-09'
start_date = datetime.strptime(START_DATE, DATE_FORMAT)

TWEETS_FILE = 'tweets.json'

TWEET_MAX_LENGTH = 115
CONGRESS_SESSION = 115

ENDPOINT = 'https://congress.api.sunlightfoundation.com/bills?congress=' + str(CONGRESS_SESSION)

SKIP_PHRASES = ('bill', 'resolution',)

PLACES = ["world's", "country's", "earth's", "history's", "our", "the", "america's",
          "our country's", "the earth's", "the world's"]
SUPERLATIVES = ['greatest', 'best', 'bravest', 'biggest', 'brightest', 'classiest', 'cleanest',
                'cleverest', 'coolest', 'fanciest', 'finest', 'grandest', 'happiest', 'humblest',
                'largest', 'newest', 'neatest', 'prettiest', 'shiniest', 'smartest', 'strongest',
                'toughest', 'wisest', 'proudest',]
ADJECTIVES = ['amazing', 'wonderful', 'tremendous', 'mindboggling', 'mind-blowing', 'stupendous',]
MODIFIERS = ['most', ]

rules = {
    'origin': '#places.capitalize# #adjective#',
    'places': PLACES,
    'adjective': [
        '#modifiers# #adjectives#', '#superlatives#'
    ],
    'modifiers': MODIFIERS,
    'adjectives': ADJECTIVES,
    'superlatives': SUPERLATIVES,
}

verbs_to_nouns = {
    'authorize': 'authorization of',
    'designate': 'designation of',
    'clarify': 'clarification of',
    'use': 'use of',
    'provide': 'provision to',
    'carry': 'carrying of',
    'improve': 'improvement of',
    'intensify': 'intensification of',
    'negotiating': 'negotiation of',
    'demonstrate': 'demonstration of',
    'amend': 'amendment to',
    'regulate': 'regulation of',
    'eliminate': 'elimination of',
    'exclude': 'exclusion of',
    'include': 'inclusion of',
    'determine': 'determination of',
    'providing': 'provision for',
    'enter': 'entry into',
    'made': 'making of',
    'honor': 'honoring of',
}
DROP_BITS = ", and for other purposes"

BILL_FILE = "bills.json"
WAIT = 2
MAX_PAGES = 40

def _auth():
    """Authorize the service with Twitter"""
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.secure = True
    auth.set_access_token(access_token, access_token_secret)
    return tweepy.API(auth)


def smart_truncate(content, length=100, suffix='…'):
    if len(content) <= length:
        return content
    else:
        return ' '.join(content[:length+1].split(' ')[0:-1]) + suffix

def download_bills(page=1):
    bills = []

    while page < MAX_PAGES:
        log.debug("Downloading page %d", page)
        resp = requests.get(ENDPOINT + "&page={}".format(page))
        data = resp.json()
        for r in data.get('results'):
            bills.append(r)
        page += 1
        time.sleep(WAIT)
    json.dump(bills, open(BILL_FILE, 'w'))

if __name__ == '__main__':

    g = tracery.Grammar(rules)
    g.add_modifiers(base_english)

    if not os.path.exists(BILL_FILE):
        download_bills()
        log.debug("Finished loading %s", BILL_FILE)
    if not os.path.exists(TWEETS_FILE):

        log.debug("Loading data file %s", BILL_FILE)
        data = json.load(open(BILL_FILE))
        log.debug("%d records loaded; starting up Spacy", len(data))

        nlp = spacy.load('en')
        tweets = []
        for r in data:
            tweet = []
            bill = {}
            number = r['bill_type'].capitalize() + '.' + str(r['number'])
            title = r['official_title']
            if title.endswith('.'):
                title = title[:-1]
            tokens = nlp(title)
            root = [w for w in tokens if w.head is w][0]
            if root.pos_ == 'NOUN':
                # This is easy, just append the rest
                remainder = str(tokens[root.i:])
                remainder = remainder.replace(DROP_BITS, "")

                tweet = '{} {} {}'.format(number.upper(),
                                          g.flatten('#origin#'),
                                          remainder)
            elif root.pos_ == 'VERB':
                dobj_pos = [i for i, x in enumerate(tokens) if x.dep == dobj]
                if len(dobj_pos) == 0:
                    log.warn("No dobj for sentence: %s", title)
                    continue
                dobj_pos = dobj_pos[0]
                # Walk backwards and get its determinative if there is one:
                det_pos = None
                test_pos = dobj_pos
                while not det_pos:
                    test_pos -= 1
                    if test_pos == 0:
                        break
                    if tokens[test_pos].dep == det:
                        det_pos = test_pos
                if det_pos:
                    dobj_pos = det_pos
                remainder = str(tokens[dobj_pos:])
                remainder = remainder.replace(DROP_BITS, "")
                if root.orth_ in verbs_to_nouns:
                    tweet = '{} {} {} {}'.format(number.upper(),
                                                 g.flatten('#origin#'),
                                                 verbs_to_nouns[root.orth_],
                                                 remainder)
            if tweet:
                tweet = smart_truncate(tweet, TWEET_MAX_LENGTH)
                tweet += " " + r['urls']['congress']
                tweets.append(tweet)

        out = []
        random.shuffle(tweets)
        for i, tweet in enumerate(tweets):
            day = start_date + timedelta(days=i)
            out.append((day.strftime('%Y-%m-%d'), tweet))
        json.dump(out, open(TWEETS_FILE, 'w'))

    api = _auth()
    tweets = json.load(open(TWEETS_FILE))
    today = datetime.now().date()

#    api.update_status(random.choice(tweets)[1])

    for line in tweets:
          date, tweet = line
          if today == datetime.strptime(date, DATE_FORMAT).date():
              api.update_status(tweet)
