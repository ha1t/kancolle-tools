# coding: utf-8
from __future__ import print_function

import os
import sys
import random
import time
from client import Client
from dock import Dock

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

def repair(client):
    dock = Dock(client);
    ship2 = client.call('/api_get_member/ship2',
                        {'api_sort_order': 2, 'api_sort_key': 1})

    # 修理時間が短い艦から入渠させる.
    member = ship2['api_data']
    member.sort(key=lambda m: m['api_ndock_time'])

    dock_no = dock.find_free_dock()
    if not dock_no:
        return

    ship = dock.find_repairable(member, ship2['api_data_deck'])
    if ship is None:
        return

    client.call('/api_req_nyukyo/start',
                {'api_ship_id': ship['api_id'],
                 'api_ndock_id': dock_no,
                 'api_highspeed': 0})

    print('dock_no=', dock_no, ' ship=', ship)

# 遠征の出撃、帰投管理を行う
def mission(client, target = {}):

    # 全艦隊の状況を取得
    deck_port = client.call('/api_get_member/deck_port')

    for port_number, mission_id in target.items():

        kantai = deck_port['api_data'][port_number]

        if kantai['api_mission'][2] == 0:
            mission_start(client, kantai['api_id'], mission_id)
        elif kantai['api_mission'][2] < (int(time.time()) * 1000):
            mission_result = client.call('/api_req_mission/result', {'api_deck_id': kantai['api_id']})
            print("遠征から帰投しました")
            supply(client)
            mission_start(client, kantai['api_id'], mission_id)
        else:
            nokori = int(str(kantai['api_mission'][2])[0:-3])
            print("遠征中:" + str(port_number) + " / 残り" + str(nokori - int(time.time())) + "秒")

# 遠征の出撃を行う
def mission_start(client, api_deck_id, api_mission_id):
    result = client.call('/api_req_mission/start',
                         {'api_deck_id': api_deck_id, 'api_mission_id': api_mission_id})
    print("遠征開始！")

# master取得用 for debug
def fetch_master():
    #ship = client.call('/api_get_master/ship')
    return None

# 対象の艦が補給対象となるかどうか
def can_supply(ship, master):
    ship_master = master.get_ship(ship['api_ship_id'])
    if ship_master['api_fuel_max'] > ship['api_fuel']:
        return True
    if ship_master['api_bull_max'] > ship['api_bull']:
        return True
    return False

# 補給を行う
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

def battle(client, deck_id = '1', mapinfo_no = '1', maparea_id = '1'):

    if is_unit_full(client):
        destroy_old_ship(client)
        if is_unit_full(client):
            print("所持数が限界に到達しました")
            os.system('nma.sh "艦これ" ERROR "所持数が限界に達しました" 1')
            sys.exit()

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

    if result['api_data']['api_get_ship_exp'][1] not in [108, 90]:
        print('異常発生。巡回を停止します')
        os.system('nma.sh "艦これ" ERROR "想定取得経験値を下回りました" 1')
        sys.exit()

def powerup(client, ship_id, id_items):
    result = client.call('/api_req_kaisou/powerup',
                        {'api_id_items': id_items, 'api_id': ship_id})

def destroy_ship(client, ship_id):
    result = client.call('/api_req_kousyou/destroyship', {'api_ship_id': ship_id})

def destroy_old_ship(client):
    master = Master()
    result = client.call('/api_get_member/ship2',
                        {'api_sort_order': 2, 'api_sort_key': 1})
    for ship in result['api_data']:
        ship_master = master.get_ship(ship['api_ship_id'])
        if ship['api_lv'] == 1:
            if ship_master['api_powup'] == [0, 1, 0, 0]:
                print(u"解体: " + ship_master['api_name'] + " / " + str(ship['api_id']))
                destroy_ship(client, ship['api_id'])
                time.sleep(3)


def is_unit_full(client):
    result = client.call('/api_get_member/record')
    if result['api_data']['api_ship'][1] == result['api_data']['api_ship'][0]:
        return True
    return False

def engage_next_ship(client):
    # 対象のshipが全回復状態か
    ship_ids = [92, 187, 240]

    # 対象のshipが編成済みかどうか
    in_deck_ships = []
    decks = client.call('/api_get_member/deck')
    deck = decks['api_data'][0]
    for in_deck_ship_id in deck['api_ship']:
        if in_deck_ship_id > -1:
            in_deck_ships.append(in_deck_ship_id)

    # 対象のshipが修復中かどうか
    repair_ships = []
    ndock = client.call('/api_get_member/ndock')
    for row in ndock['api_data']:
        repair_ships.append(row['api_ship_id'])

    target_ship_id = -1
    for ship_id in ship_ids:
        if ship_id in in_deck_ships:
                continue
        if ship_id in repair_ships:
                continue
        target_ship_id = ship_id

    result = client.call('/api_req_hensei/change',
                         {'api_ship_id': target_ship_id, 'api_ship_idx': '0', 'api_id': '1'})
    print(result)
    sys.exit()

class AutoTool(object):

    def __init__(self, token):
        self.client = Client(token)
        self.master = Master()

        print('initialize...')
        #self.ship2 = client.call('/api_get_member/ship2',
        #                         {'api_sort_order': 2, 'api_sort_key': 1})

    def crawl(self):

        #destroy_old_ship(self.client)
        #engage_next_ship(self.client)
        #sys.exit()

        while True:
            sleep_time = 300

            #battle(self.client)

            repair(self.client)
            supply(self.client)
            mission(self.client, {1: '5', 2: '6', 3: '9'})
            time.sleep(sleep_time)

def main():
    auto_tool = AutoTool(sys.argv[1])
    auto_tool.crawl()
    sys.exit()

if __name__ == '__main__':
    main()
