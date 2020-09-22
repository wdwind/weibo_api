# -*- coding: utf-8 -*-

import logging
import sys
import time

from weibo_api import WeiboCnApi


def post():
    weibo = WeiboCnApi(login_user='user', login_password='password', weibo_cn_session_file='./session.pkl')
    pic_id = weibo.get_pic_id('./zyene.png')
    response = weibo.post_status("test post " + str(time.time()), [pic_id])
    print('Response status: %s. (1 means successful.)' % response.get('ok', 'Unknown error'))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    post()
