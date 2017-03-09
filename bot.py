import json
import random
import logging

import requests
import spacy
import tracery
from tracery.modifiers import base_english

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)

nlp = spacy.load('en')

ENDPOINT = 'https://congress.api.sunlightfoundation.com/bills?congress=115'

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

if __name__ == '__main__':

    g = tracery.Grammar(rules)
    g.add_modifiers(base_english)
    resp = requests.get(ENDPOINT)
    data = resp.json()
    bills = []
    for r in data['results']:
        bill = {}
        bill['number'] = r['bill_type'].capitalize() + '.' + str(r['number'])
        title = r['official_title']
        tokens = nlp(title)
        for chunk in tokens.noun_chunks:
            print(chunk.orth_)
        bills.append(bill)
    pick = random.choice(bills)
#    print('{} {} {} of 2017'.format(pick['number'], g.flatten('#origin#'), pick['title'],))
