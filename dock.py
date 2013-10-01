# coding: utf-8
from __future__ import print_function

class Dock(object):

    def __init__(self, client):
        self.client = client
        self.update()

    def update(self):
        print('入渠ドック情報を取得')
        ndock = self.client.call('/api_get_member/ndock')
        self.docks = ndock['api_data']

    # 入渠可能なドックを返す
    def find_free_dock(self):
        for dock in self.docks:
            if dock['api_state'] == 0:
                return dock['api_id']
        return None

    def find_repairable(self, member, decks):
        u"""入渠する艦を選んでその ship を返す."""
        cant_repair = set()

        # 編成されてる艦を入渠するとバレるのでしない.
        for deck in decks:
            cant_repair.update(deck['api_ship'])

        # 修理中の艦ももちろん入渠しない.
        for dock in self.docks:
            cant_repair.add(dock['api_ship_id'])

        for ship in member:
            if ship['api_nowhp'] >= ship['api_maxhp']:
                continue
            ship_id = ship['api_id']
            if ship_id in cant_repair:
                continue
            return ship
        return None

