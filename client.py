# coding: utf-8
from __future__ import print_function

import time
import json
import requests

class Client(object):
    #prefix = 'http://203.104.105.167/kcsapi'
    prefix = 'http://203.104.248.135/kcsapi'
    version = '1.4.2'
    wait_time = 1
    call_count = 0

    def __init__(self, token):
        self.session = requests.session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36',
            'Origin': 'http://203.104.105.167',
            'Referer': 'http://203.104.105.167/kcs/port.swf?version=' + self.version,})
        self.base_data = {'api_verno': 1, 'api_token': token}

    def call(self, path, data=None):
        time.sleep(self.wait_time)
        if data is None:
            data = {}
        data.update(self.base_data)
        res = self.session.post(self.prefix + path, data)
        self.call_count = self.call_count + 1
        res.raise_for_status()
        resdata = res.text
        if not resdata.startswith('svdata='):
            return None
            raise NotExpectedResult(resdata)
        resjson = json.loads(resdata[7:])
        if resjson['api_result'] != 1:
            if 'api_result_msg' in resjson:
                print(resjson['api_result_msg'])
            raise NotExpectedResult(resdata)
        return resjson

