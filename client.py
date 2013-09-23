# coding: utf-8
from __future__ import print_function

import json
import requests

class Client(object):
    #prefix = 'http://203.104.105.167/kcsapi'
    prefix = 'http://203.104.248.135/kcsapi'
    version = '1.4.2'

    def __init__(self, token):
        self.session = requests.session()
        self.session.headers.update({
            'Uesr-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36',
            'Origin': 'http://203.104.105.167',
            'Referer': 'http://203.104.105.167/kcs/port.swf?version=' + self.version,})
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

