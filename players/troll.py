# coding: utf-8
from things import Player


class Troll(Player):
    '''A player that always heals itself.

       (trolls have regenerative capabilities, hence the name).
    '''
    def next_step(self, things):
        self.status = u'healing myself'
        return 'heal', self


def create(rules, objetives=None):
    return Troll('troll', 'blue')
