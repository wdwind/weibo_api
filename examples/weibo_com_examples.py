# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboComApi


def post():
    weibo = WeiboComApi(login_user='user', login_password='password')
    vid = weibo.upload_video('video.mp4')
    pid = weibo.upload_pic('zyene.jpg')
    response = weibo.post_status('test post' + str(time.time()), vid, pid)
    print('Response status: %s. (100000 means successful.)' % response.get('code', 'Unknown error'))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
