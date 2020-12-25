# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboComApi


def post():
    weibo = WeiboComApi(weibo_session_file='./weibo_session.pkl')
    vid = weibo.upload_video('video.mp4')
    pid = weibo.upload_pic('zyene.png')
    response = weibo.post_status('test post' + str(time.time()), vid, pid)
    print(f'Response status: {response.get("code", "Unknown error")}. (100000 means successful.)')


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
