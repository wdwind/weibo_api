# -*- coding: utf-8 -*-

import base64
import binascii
import hashlib
import http.cookiejar
import json
import logging
import os
import random
import re
import time
from collections import OrderedDict
from os.path import getsize

import requests
import rsa

from ..simple_captcha.weibo_com_captcha import WeiboComCaptcha
from ..requests_wrapper import RequestsWrapper
from .weibo_com_api_constants import *

try:
    from urllib.parse import parse_qs, urlparse
except ImportError:  # Python 2
    from urlparse import parse_qs, urlparse


class LoginException(Exception):
    pass


class WeiboComApi(RequestsWrapper):
    """weibo.com API for video upload"""

    login_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'}
    post_headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'http://weibo.com',
            'Referer': 'http://weibo.com/?topnav=1&wvr=6&mod=logo',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'}

    def __init__(self, **kwargs):
        self.login_user = kwargs.get('login_user', None)
        self.login_password = kwargs.get('login_password', None)

        self.logger = logging.getLogger(__name__)

        self.captcha_cracker = WeiboComCaptcha(save_captcha=kwargs.get('save_captcha', False))

        self.timeout = kwargs.get('timeout', 60)
        self.session = requests.Session()
        self.cookie_file = kwargs.get('weibo_com_cookie_file', None)
        self.session.cookies = http.cookiejar.LWPCookieJar(self.cookie_file)
        self.login_constants = {}

        if self.cookie_file and os.path.isfile(self.cookie_file):
            # Currently cookies not working...
            self.session.cookies.load(ignore_expires=True)
        else:
            if not self.login_user or not self.login_password:
                raise LoginException('Login required.')
            self.login()

    def prelogin(self):
        params = {
            '_': time.time(),
            'callback': 'sinaSSOController.preloginCallBack',
            'checkpin': 1,
            'client': 'ssologin.js(v1.4.19)',
            'entry': 'weibo',
            'rsakt': 'mod',
            'su': self.su
        }
        rsp = self.get(PRELOGIN_URL, params=params, headers=WeiboComApi.login_headers, timeout=self.timeout).text
        self.login_constants = json.loads(re.findall(r'preloginCallBack\(([\w\W]+?)\)', rsp)[0])

    def login(self):
        self.prelogin()
        data = {
            'encoding': 'UTF-8',
            'entry': 'weibo',
            'from': '',
            'gateway': 1,
            'nonce': self.login_constants.get('nonce', ''),
            'pagerefer': LOGIN_PAGE_REFERER,
            'prelt': 3179,
            'pwencode': 'rsa2',
            'qrcode_flag': False,
            'returntype': 'TEXT',
            'rsakv': self.login_constants.get('rsakv', ''),
            'savestate': 7,
            'servertime': self.login_constants.get('servertime', ''),
            'service': 'miniblog',
            'sp': self.encrypted_pwd,
            'sr': '1280*720',
            'su': self.su,
            'url': LOGIN_PARAMS_URL,
            'useticket': 1,
            'vsnf': 1,
        }

        pin = ''
        if self.login_constants.get('showpin', 0) == 1:
            pin = self.get_pin()
            data['door'] = pin
            data['cdult'] = 2
            data['pcid'] = self.login_constants['pcid']
            data['prelt'] = 2041

        rsp = self.post(LOGIN_URL, data=data, headers=WeiboComApi.login_headers, timeout=self.timeout).json()
        if rsp['retcode'] != '0':
            if rsp['retcode'] == '2070' and rsp['reason'] == u'输入的验证码不正确':
                self.logger.error('Wrong captcha: %s. Reporting...', pin)
                self.captcha_cracker.report_wrong_result(pin)
            raise LoginException('Wrong retcode. Login failed.')

        self.get(SSO_LOGIN_URL, headers=WeiboComApi.login_headers, timeout=self.timeout)
        params = {
            'callback': 'sinaSSOController.doCrossDomainCallBack',
            'client': 'ssologin.js(v1.4.19)',
            'display': 0,
            'ticket': rsp['ticket'],
            'retcode': 0,
            'ssosavestate': 7,
            'url': LOGIN_PARAMS_URL_WITH_REF
        }
        self.get(LOGIN_PASSPORT, params=params, headers=WeiboComApi.login_headers, timeout=self.timeout)
        self.get(LOGIN_PARAMS_URL_WITH_REF, headers=WeiboComApi.login_headers, timeout=self.timeout)
        # interest = self.get(INTEREST_URL, timeout=self.timeout)
        # uid = re.search(r"CONFIG\['uid'\]='([^']+)'", interest.text).group(1)
        # nick = re.search(r"CONFIG\['nick'\]='([^']+)'", interest.text).group(1)
        if self.cookie_file:
            self.session.cookies.save(filename=self.cookie_file, ignore_discard=True, ignore_expires=True)
        self.logger.info('Weibo.com Login succeeded.')

    # Currently useless since loading cookies doesn't work
    # def is_login(self):
    #     response = self.get(WEIBO_URL, headers=WeiboComApi.login_headers)
    #     if u'我的首页' in response.text:
    #         return True
    #     else:
    #         return False

    def get_pin(self):
        """
        Get captcha pic
        """
        para = {
            'p': self.login_constants['pcid'],
            'r': random.randint(10000, 100000),
            's': 0
        }
        pic = self.get(GET_PIN_URL, params=para, headers=WeiboComApi.login_headers, timeout=self.timeout)
        pin = self.captcha_cracker.predict(pic.content)
        self.logger.info('Weibo.com captcha: %s', pin)
        return pin

    def upload_init(self, filename):
        with open(filename, 'rb') as f:
            params = {
                "length": getsize(filename),
                "check": WeiboComApi.__calc_MD5(f.read()),
                "type": 'video',
                "source": 2637646381,
                "name": filename,
                'client': 'web',
                'mediaprops': '{"screenshot":0,"video_type":"normal"}',
                "status": 'wired',
                "ua": self.session.headers['User-Agent'],
                "count": 1
            }
        res = self.post(MULTIMEDIA_INIT_URL, params=params, timeout=self.timeout)
        init_info = res.json()
        if 'error' in init_info:
            self.login()
            raise LoginException('Error in video upload initialization. Response: %s', res.content)
        return init_info

    def upload_video(self, filename):
        init_info = self.upload_init(filename)
        file_token = init_info['fileToken']
        chunk_size = init_info['length']
        with open(filename, 'rb') as f:
            start_location = 0
            while True:
                chunk = f.read(chunk_size * 1024)
                flag = self.__upload_data(file_token, start_location, chunk)
                start_location += chunk_size * 1024
                if flag is True:
                    continue
                else:
                    if flag is not None:
                        return flag

    def __upload_data(self, file_token, start_location, chunk):
        params = {
            'source': 2637646381,
            'filetoken': file_token,
            'sectioncheck': WeiboComApi.__calc_MD5(chunk),
            'startloc': start_location,
            'client': 'web',
            'status': 'wired',
            'ua': WeiboComApi.login_headers['User-Agent'],
            'v': WeiboComApi.__get_unique_key()
        }
        rsp = self.post(MULTIMEDIA_UPLOAD_DATA_URL, params=params, data=chunk, timeout=10*self.timeout).json()
        try:
            return rsp['succ']
        except:
            try:
                return rsp['fid']
            except:
                return None

    def upload_pic(self, filename):
        params = {
            'cb': 'http://weibo.com/aj/static/upimgback.html?_wv=5&callback=STK_ijax_'
                  + WeiboComApi.__get_unique_key() + '21',
            'mime': 'image/jpeg',
            'data': 'base64',
            'url': 0,
            'markpos': 1,
            'logo': '',
            'nick': 0,
            'marks': 1,
            'app': 'miniblog',
            's': 'rdxt',
            'file_source': 10
        }

        with open(filename, 'rb') as f:
            data = {'b64_data': base64.b64encode(f.read())}
            rsp = self.post(MULTIMEDIA_UPLOAD_PIC_URL, params=params, data=data, timeout=self.timeout)
            return parse_qs(urlparse(rsp.url).query)['pid'][0]

    def post_status(self, caption, video_id, pic_id, tags=None):
        if len(caption) <= 6:
            raise ValueError('Video caption must contain at least 6 characters. Caption: %s', caption)

        data = OrderedDict([
            ('location', 'v6_group_content_home'),
            ('text', caption),
            ('appkey', ''),
            ('style_type', 1),
            ('pic_id', ''),
            ('tid', ''),
            ('mid', ''),
            ('isReEdit', 'false'),
            ('pdetail', ''),
            ('video_fid', video_id),
            ('video_titles', caption),
            ('video_tags', '' if tags is None else "|".join(tags)),
            ('video_covers', "http://wx3.sinaimg.cn/large/" + pic_id + ".jpg|640|360"),
            ('video_monitor', 1),
            ('album_ids', ''),
            ('rank', 0),
            ('rankid', ''),
            ('module', 'stissue'),
            ('pub_source', 'main_'),
            ('pub_type', 'dialog'),
            ('isPri', 0),
            ('_t', 0)
        ])
        params = OrderedDict([
            ('ajwvr', 6),
            ('__rnd', int(time.time() * 1000))
        ])

        rsp = self.post(POST_WEIBO_URL, data=data, params=params, timeout=self.timeout,
                        allow_redirects=True, headers=WeiboComApi.post_headers)

        try:
            rsp_data = rsp.json()
        except:
            self.login()
            raise LoginException('Error posting video %s. Login again. Response: %s', caption, rsp.content)

        if rsp_data['code'] == '100000':
            self.logger.info('Weibo %s is posted', caption)
        else:
            self.logger.error('Error posting weibo %s. Response: %s', caption, rsp_data)
        return rsp_data

    @property
    def su(self):
        """
        Get encoded username
        """
        return base64.encodestring(self.login_user.encode("utf-8"))[:-1]

    @property
    def encrypted_pwd(self):
        """
        Get encrypted password
        """
        rsa_pubkey = int(self.login_constants.get('pubkey', ''), 16)
        RSAKey = rsa.PublicKey(rsa_pubkey, 65537)  # Create public key
        secret = str(self.login_constants.get('servertime', '')) + '\t' + \
                 str(self.login_constants.get('nonce', '')) + '\n' + str(self.login_password)
        pwd = rsa.encrypt(secret.encode("utf-8"), RSAKey)  # Encrypt with RSA
        return binascii.b2a_hex(pwd)  # Convert encrypted data to HEX

    @staticmethod
    def __calc_MD5(file_content):
        md5obj = hashlib.md5()
        md5obj.update(file_content)
        return md5obj.hexdigest()

    @staticmethod
    def __get_unique_key():
        return str(int(time.time() * 1000)) + str(random.randint(0, 99))
