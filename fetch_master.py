# coding: utf-8
from __future__ import print_function

import sys
from client import Client

# master取得用 for debug
def fetch_master(client):
    ship = client.call('/api_get_master/ship')

    fp = open('master_ship.txt', 'w')
    fp.write(str(ship))
    fp.close()

def main():
    client = Client(sys.argv[1])
    fetch_master(client)

if __name__ == '__main__':
    main()
