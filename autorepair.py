# coding: utf-8
from __future__ import print_function

import sys
import random
import requests
import json
import time

class NotExpectedResult(Exception):
    pass

class Master(object):

    def __init__(self):
        fp = open('master.txt')
        text = fp.read()
        self.master = eval(text)

    def get_ship(self, ship_id):
        for ship in self.master['api_data']:
            if ship['api_id'] == ship_id:
                return ship
        raise NotExpectedResult(ship_id)

class Client(object):
    #prefix = 'http://203.104.105.167/kcsapi'
    prefix = 'http://203.104.248.135/kcsapi'

    def __init__(self, token):
        self.session = requests.session()
        self.session.headers.update({
            'Uesr-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36',
            'Origin': 'http://203.104.105.167',
            'Referer': 'http://203.104.105.167/kcs/port.swf?version=1.3.9',})
        self.base_data = {'api_verno': 1, 'api_token': token}

    def call(self, path, data=None):
        if data is None:
            data = {}
        data.update(self.base_data)
        res = self.session.post(self.prefix + path, data)
        res.raise_for_status()
        resdata = res.text
        if not resdata.startswith('svdata='):
            return None
            raise NotExpectedResult(resdata)
        resjson = json.loads(resdata[7:])
        if resjson['api_result'] != 1:
            raise NotExpectedResult(resdata)
        return resjson


def find_free_dock(docks):
    for d in docks:
        if d['api_state'] == 0:
            return d['api_id']
    return None


def find_repairable(member, decks, docks):
    u"""入渠する艦を選んでその ship を返す."""
    cant_repair = set()

    # 編成されてる艦を入渠するとバレるのでしない.
    #for deck in decks:
        #cant_repair.update(deck['api_ship'])

    # 修理中の艦ももちろん入渠しない.
    for dock in docks:
        cant_repair.add(dock['api_ship_id'])

    for ship in member:
        if ship['api_nowhp'] >= ship['api_maxhp']:
            continue
        ship_id = ship['api_id']
        if ship_id in cant_repair:
            continue
        return ship
    return None

def can_supply(ship, master):
    ship_master = master.get_ship(ship['api_ship_id'])
    if ship_master['api_fuel_max'] > ship['api_fuel']:
        return True
    if ship_master['api_bull_max'] > ship['api_bull']:
        return True
    return False

def repair(client):
    ndock = client.call('/api_get_member/ndock')
    ship2 = client.call('/api_get_member/ship2',
                        {'api_sort_order': 2, 'api_sort_key': 1})

    # 修理時間が短い艦から入渠させる.
    member = ship2['api_data']
    member.sort(key=lambda m: m['api_ndock_time'])

    dock_no = find_free_dock(ndock['api_data'])
    ship = find_repairable(member, ship2['api_data_deck'], ndock['api_data'])

    if not dock_no:
        return

    if ship is None:
        return

    print('dock_no=', dock_no, ' ship=', ship)

    client.call('/api_req_nyukyo/start',
                {'api_ship_id': ship['api_id'],
                 'api_ndock_id': dock_no,
                 'api_highspeed': 0})

def mission(client):
    deck_port = client.call('/api_get_member/deck_port')
    dai2kantai = deck_port['api_data'][1]
    if dai2kantai['api_mission'][2] == 0:
        print("出撃可能")
        try:
            result = client.call('/api_req_mission/start',
                                 {'api_deck_id': dai2kantai['api_id'], 'api_mission_id': '5'})
            print(result)
        except:
            print('出撃')
    elif dai2kantai['api_mission'][2] < (int(time.time()) * 1000):
        mission_result = client.call('/api_req_mission/result', {'api_deck_id': dai2kantai['api_id']})
        print(mission_result)
        supply(client)
    else:
        print("遠征中")

def mission_clear(client):
    mission_result = client.call('/api_req_mission/result')
    print(mission_result)

def fetch_master():
    #ship = client.call('/api_get_master/ship')
    return None

def supply(client):
    ship_ids = []
    master = Master()
    ship2 = client.call('/api_get_member/ship2',
                        {'api_sort_order': 2, 'api_sort_key': 1})
    for ship in ship2['api_data']:
        if can_supply(ship, master):
            ship_ids.append(str(ship['api_id']))

    for ship_id in ship_ids:
        result = client.call('/api_req_hokyu/charge', {'api_kind': 3, 'api_id_items': ship_id})
        print(result)
        time.sleep(3)

def battle(client):
    result = client.call('/api_req_map/start', {'api_formation_id': '1', 'api_deck_id': '1', 'api_maparea_id': '1', 'api_mapinfo_no': '1'})
    print(result)
    time.sleep(5)

    result = client.call('/api_req_sortie/battle', {'api_formation': '1'})
    print(result)
    time.sleep(5)

    result = client.call('/api_req_sortie/battleresult')
    print(result)
    time.sleep(5)

    supply(client)
def main():
    client = Client(sys.argv[1])
    while True:
        #battle(client)
        #battle(client)
        #battle(client)
        #battle(client)
        #battle(client)

        repair(client)
        supply(client)
        mission(client)
        time.sleep(234)

# https://gist.github.com/oh-sky/6404680/raw/04761c89fe63d5935a3102e900bf5812d1a3b158/knkr.rb
# http://www.kirishikistudios.com/?p=154

if __name__ == '__main__':
    main()
