# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboCnApi


def post():
    weibo = WeiboCnApi(login_user='user', login_password='password')
    response = weibo.post_status_pic_files("test post " + str(time.time()), ['./zyene.png'])
    print(response)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
