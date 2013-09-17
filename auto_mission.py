# coding: utf-8
from __future__ import print_function

import os
import sys
import random
import time
from client import Client

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

def find_free_dock(docks):
    for d in docks:
        if d['api_state'] == 0:
            return d['api_id']
    return None

def find_repairable(member, decks, docks):
    u"""入渠する艦を選んでその ship を返す."""
    cant_repair = set()

    # 編成されてる艦を入渠するとバレるのでしない.
    for deck in decks:
        cant_repair.update(deck['api_ship'])

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

# 対象の艦が補給対象となるかどうか
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

def mission(client, port_number, misson_id):
    deck_port = client.call('/api_get_member/deck_port')
    dai2kantai = deck_port['api_data'][port_number]
    if dai2kantai['api_mission'][2] == 0:
        print("出撃可能")
        try:
            result = client.call('/api_req_mission/start',
                                 {'api_deck_id': dai2kantai['api_id'], 'api_mission_id': misson_id})
            print(result)
        except:
            print('出撃')
    elif dai2kantai['api_mission'][2] < (int(time.time()) * 1000):
        mission_result = client.call('/api_req_mission/result', {'api_deck_id': dai2kantai['api_id']})
        print(mission_result)
        supply(client)
    else:
        print("遠征中:" + str(dai2kantai['api_mission'][2] - (int(time.time()) * 1000)))

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
        if result['api_result'] != 1:
            print(result)
        print("補給完了:" + str(result['api_data']['api_ship'][0]['api_id']) + " " + str(result['api_data']['api_material']))
        time.sleep(3)

def battle(client, deck_id = '1'):
    #mapinfo_no = '3'
    #maparea_id = '2'

    mapinfo_no = '1'
    maparea_id = '1'
    result = client.call('/api_req_map/start',
                         {'api_formation_id': '1', 'api_deck_id': deck_id, 'api_maparea_id': maparea_id, 'api_mapinfo_no': mapinfo_no})
    print(str(result['api_data']['api_mapinfo_no']) + "-" + str(result['api_data']['api_maparea_id']))
    print(result['api_data'])

    if result['api_data'].has_key('api_itemget'):
        print("アイテムゲット！")
        result = client.call('/api_req_map/next')
        print(result)
    time.sleep(5)

    result = client.call('/api_req_sortie/battle', {'api_formation': '1'})
    print(result['api_data']['api_maxhps'])
    print(result['api_data']['api_nowhps'])
    time.sleep(5)

    result = client.call('/api_req_sortie/battleresult')
    print('---')
    print(result['api_data']['api_get_ship_exp'])
    print(result['api_data']['api_get_exp_lvup'])
    print('---')

    supply(client)
    time.sleep(5)

    if result['api_data']['api_get_ship_exp'][1] != 108:
        print('異常発生。巡回を停止します')
        os.system('nma.sh "艦これ" auto ' + time.strftime("%H-%M-%S"))
        sys.exit()

def main():
    client = Client(sys.argv[1])
    while True:
        sleep_time = 200

        #battle(client)
        #battle(client)
        #battle(client)
        #battle(client)
        #battle(client)

        repair(client)
        supply(client)
        mission(client, 1, '5')
        mission(client, 2, '3')
        time.sleep(sleep_time)

# https://gist.github.com/oh-sky/6404680/raw/04761c89fe63d5935a3102e900bf5812d1a3b158/knkr.rb
# http://www.kirishikistudios.com/?p=154

if __name__ == '__main__':
    main()
