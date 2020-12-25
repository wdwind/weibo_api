# -*- coding: utf-8 -*-

import logging
import sys

from weibo_api.weibo_login import WeiboLoginApi


def is_login(weibo):
    print(f'weibo.com logged in? {weibo.is_com_login()}')
    print(f'weibo.cn logged in? {weibo.is_cn_login()}')


def weibo_com_private_msg_login(username, password):
    weibo = WeiboLoginApi(login_user=username, login_password=password,
                          verification_type='private_msg', weibo_session_file='./weibo_com_private_msg_session.pkl')
    weibo.weibo_com_login()
    is_login(weibo)


def weibo_com_sms_login(username, password):
    weibo = WeiboLoginApi(login_user=username, login_password=password,
                          verification_type='sms', weibo_session_file='./weibo_com_sms_session.pkl')
    weibo.weibo_com_login()
    is_login(weibo)


def weibo_cn_private_msg_login(username, password):
    weibo = WeiboLoginApi(login_user=username, login_password=password,
                          verification_type='private_msg', weibo_session_file='./weibo_cn_private_msg_session.pkl')
    weibo.weibo_cn_login()
    is_login(weibo)


def weibo_cn_sms_login(username, password):
    weibo = WeiboLoginApi(login_user=username, login_password=password,
                          verification_type='sms', weibo_session_file='./weibo_cn_sms_session.pkl')
    weibo.weibo_cn_login()
    is_login(weibo)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    username = ''
    password = ''
    # weibo_com_private_msg_login(username, password)
    # weibo_com_sms_login(username, password)
    # weibo_cn_private_msg_login(username, password)
    # weibo_cn_sms_login(username, password)
