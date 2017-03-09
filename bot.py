from __future__ import print_function, unicode_literals

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

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

CONGRESS_SESSION = 115
ENDPOINT = 'https://congress.api.sunlightfoundation.com/bills?congress=' + str(CONGRESS_SESSION)

SKIP_PHRASES = ('bill', 'resolution',)

PLACES = ["world's", "country's", "earth's", "history's", "our",]
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

BILL_FILE = "bills.json"
WAIT = 2
MAX_PAGES = 20

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

    log.debug("Loading data file %s", BILL_FILE)
    data = json.load(open(BILL_FILE))
    log.debug("%d records loaded; starting up Spacy", len(data))

    nlp = spacy.load('en')
    bills = []
    for r in data:
        bill = {}
        bill['number'] = r['bill_type'].capitalize() + '.' + str(r['number'])
        title = r['official_title']
        tokens = nlp(title)
        root = [w for w in tokens if w.head is w][0]
        if root.pos_ == 'VERB':
            dobj_pos = [i for i, x in enumerate(tokens) if x.dep == dobj]
            if len(dobj_pos) == 0:
                log.warn("No dobj for sentence: %s", title)
                continue
            dobj_pos = dobj_pos[0]
            # Walk backwards and get its determinative if there is one:
            if tokens[dobj_pos - 1].dep == det:
                dobj_pos -= 1
            remainder = tokens[dobj_pos:]
            if root.orth_ in verbs_to_nouns:
                log.debug(title)
                print('{} {} {} {} of 2017'.format(bill['number'].upper(),
                                                g.flatten('#origin#'),
                                                verbs_to_nouns[root.orth_],
                                                remainder))
                print()
            #    bills.append(bill)
#    pick = random.choice(bills)
#    print('{} {} {} of 2017'.format(pick['number'], g.flatten('#origin#'), pick['title'],))
