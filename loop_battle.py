# coding: utf-8
from __future__ import print_function
from pprint import pprint

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
        fp = open('master_ship.txt')
        text = fp.read()
        fp.close()
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

    minimum_sleep_time = 999999999

    for port_number, mission_id in target.items():

        kantai = deck_port['api_data'][port_number]

        if kantai['api_mission'][2] == 0:
            mission_start(client, kantai['api_id'], mission_id)
            continue

        if kantai['api_mission'][2] < (int(time.time()) * 1000):
            mission_result = client.call('/api_req_mission/result', {'api_deck_id': kantai['api_id']})
            print("遠征から帰投しました")
            supply(client)
            mission_start(client, kantai['api_id'], mission_id)
            continue

        nokori = int(str(kantai['api_mission'][2])[0:-3]) - int(time.time())
        print("遠征中:" + str(port_number) + " / 残り" + str(nokori) + "秒")

        if minimum_sleep_time > nokori:
            minimum_sleep_time = nokori

    return minimum_sleep_time

# 遠征の出撃を行う
def mission_start(client, api_deck_id, api_mission_id):
    result = client.call('/api_req_mission/start',
                         {'api_deck_id': api_deck_id, 'api_mission_id': api_mission_id})
    print("遠征開始！")

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


# @TODO 艦隊数が1だったらcondを気にしない。
def battle(client, deck_id = '1', maparea_id = '1', mapinfo_no = '1'):

    if is_unit_full(client):
        destroy_old_ship(client)
        if is_unit_full(client):
            print("所持数が限界に到達しました")
            os.system('nma.sh "艦これ" ERROR "所持数が限界に達しました" 1')
            sys.exit()

    # 艦隊のコンディションが悪い時はバトルしない 
    #if not is_good_condition(client, deck_id):
    #    return None

    result = client.call('/api_req_map/start',
                         {'api_formation_id': '1', 'api_deck_id': deck_id, 'api_maparea_id': maparea_id, 'api_mapinfo_no': mapinfo_no})
    print(result['api_data']['api_maparea_id'], "-", result['api_data']['api_mapinfo_no'])
    print(result['api_data'])

    if result['api_data'].has_key('api_itemget'):
        print("アイテムゲット！")
        result = client.call('/api_req_map/next')
        print(result)
    time.sleep(4)

    result = client.call('/api_req_sortie/battle', {'api_formation': '1'})['api_data']
    print(result['api_maxhps'])
    print(result['api_nowhps'])
    #pprint(result)
    time.sleep(6)

    result = client.call('/api_req_sortie/battleresult')['api_data']
    print('---')
    print(result['api_get_ship_exp'])
    print(result['api_get_exp_lvup'])
    pprint(result)
    print('---')

    result = client.call('/api_auth_member/logincheck')
    print('login check')

    result = client.call('/api_get_member/basic')
    print(result)

    supply(client)
    time.sleep(5)

    #if result['api_win_rank'] != 'S':
    if not result['api_win_rank'] in ['S', 'A', 'B']:
        print('異常発生。巡回を停止します')
        os.system('nma.sh "艦これ" ERROR "想定取得経験値を下回りました" 1')
        sys.exit()


    #if result['api_get_ship_exp'][1] not in [108, 90]:
    #    print('異常発生。巡回を停止します')
    #    os.system('nma.sh "艦これ" ERROR "想定取得経験値を下回りました" 1')
    #    sys.exit()

# 近代化改修
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
    result = client.call('/api_get_member/record')['api_data']
    if result['api_ship'][1] == result['api_ship'][0]:
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

class Ship2(object):

    def __init__(self, client):

        self.client = client
        self.update()

        #for ship in self.ship_data:
        #    print(ship['api_cond'])
        #sys.exit()

    def update(self):
        self.ship_data = self.client.call('/api_get_member/ship2',
                                     {'api_sort_order': 2, 'api_sort_key': 1})['api_data']

    def get_ship(self, api_id):
        for ship in self.ship_data:
            if ship['api_id'] == api_id:
                return ship

# 指定艦隊のコンディションが微妙かどうかチェックする
def is_good_condition(client, deck_id):
    result = client.call('/api_auth_member/logincheck')
    deck_ship_ids = client.call('/api_get_member/deck_port')['api_data'][deck_id - 1]['api_ship']
    ship2 = Ship2(client)
    for api_id in deck_ship_ids:
        ship = ship2.get_ship(api_id)
        if ship['api_cond'] >= 40:
            return True

    return False

class AutoTool(object):

    def __init__(self, token):
        self.client = Client(token)
        self.master = Master()

        print('initialize...')

    def crawl(self):

        while True:
            sleep_time = 300

            if self.client.call_count > 50:
                self.client.call_count = 0
                result = self.client.call('/api_auth_member/logincheck')
                print('login check')
                time.sleep(5)

            battle(self.client, 1, 1, 1)

            # 潜水艦要
            #battle(self.client, 1, 2, 3)

            #battle(self.client, 1, 3, 2)
            #battle(self.client, 1, 2, 4)
            #sys.exit()
            continue

            repair(self.client)
            supply(self.client)
            #mission_sleep_time = mission(self.client, {1: '5', 2: '6', 3: '9'})
            #mission_sleep_time = mission(self.client, {1: '2', 2: '4', 3: '9'})

            # バランス(バケツ多め、鋼少なめ)
            #mission_sleep_time = mission(self.client, {1: '7', 2: '4', 3: '5'})

            mission_sleep_time = mission(self.client, {1: '14', 2: '3', 3: '5'})

            if sleep_time > mission_sleep_time:
                # 処理が速すぎると帰投してないみたいなので1秒wait
                sleep_time = mission_sleep_time + 1

            print(str(sleep_time) + '秒スリーブ')
            time.sleep(sleep_time)

def main():
    auto_tool = AutoTool(sys.argv[1])
    auto_tool.crawl()
    sys.exit()

if __name__ == '__main__':
    main()
