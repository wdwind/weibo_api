# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboCnApi


def post():
    weibo = WeiboCnApi(weibo_session_file='./weibo_session.pkl')
    pic_id = weibo.get_pic_id('./zyene.png')
    response = weibo.post_status("test post " + str(time.time()), [pic_id])
    print(f'Response status: {response.get("ok", "Unknown error")}. (1 means successful.)')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
