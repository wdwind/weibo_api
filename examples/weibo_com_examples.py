# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboComApi


def post():
    weibo = WeiboComApi(login_user='user', login_password='password')
    response = weibo.post_weibo('test post' + str(time.time()), 'video.mp4', 'zyene.jpg')
    print(response)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
