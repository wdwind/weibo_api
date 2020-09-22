# -*- coding: utf-8 -*-

import copy
import json
import logging
import mimetypes
import ntpath
import os
import pickle
import time

import requests
from PIL import Image
from requests_toolbelt import MultipartEncoder

try:
    from io import BytesIO
except ImportError:
    from StringIO import StringIO as BytesIO

from ..requests_wrapper import RequestsWrapper
from .weibo_cn_api_constants import *


class LoginException(Exception):
    pass


class WeiboCnApi(RequestsWrapper):
    """m.weibo.cn API"""

    COMMON_HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36',
    }

    def __init__(self, **kwargs):
        self.login_user = kwargs.get('login_user', None)
        self.login_password = kwargs.get('login_password', None)

        self.logger = logging.getLogger(__name__)

        self.timeout = kwargs.get('timeout', 60)
        self.session_file = kwargs.get('weibo_cn_session_file', None)
        self.session = self.load_session()
        if not self.is_login():
            if not self.login_user or not self.login_password:
                raise RuntimeError('Provide username and password to login.')
            self.login()

    def login(self):
        """Login to m.weibo.cn. token is not needed here."""
        url1 = 'https://passport.sina.cn/sso/login'
        headers1 = copy.deepcopy(WeiboCnApi.COMMON_HEADERS)
        headers1.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://passport.sina.cn',
            'Referer': 'https://passport.sina.cn/signin/signin',
        })
        form_data = {
            'username': self.login_user,
            'password': self.login_password,
            'savestate': 1,
            'ec': 1,
            'pagerefer': '',
            'entry': 'wapsso',
            'sinacnlogin': 1,
        }
        r1 = self.post(url1, headers=headers1, data=form_data, timeout=self.timeout)
        r1_data = json.loads(r1.content)
        if r1_data['retcode'] == 20000000:
            url2 = r1_data['data']['loginresulturl'] + '&savestate=1&url=https://sina.cn'
            r2 = self.get(url2, headers=WeiboCnApi.COMMON_HEADERS, timeout=self.timeout)
            url3 = 'https://sina.cn'
            r3 = self.get(url3, headers=WeiboCnApi.COMMON_HEADERS, timeout=self.timeout)
            url4 = 'https://m.weibo.cn/?vt=4&pos=108'
            r4 = self.get(url4, headers=WeiboCnApi.COMMON_HEADERS, timeout=self.timeout)
            url5 = 'https://m.weibo.cn/api/config'
            r5 = self.get(url5, headers=WeiboCnApi.COMMON_HEADERS, timeout=self.timeout)
            r5_data = json.loads(r5.content)
            if not r5_data['data']['login']:
                raise LoginException('Login to m.weibo.cn failed.')
        else:
            raise LoginException('Login to m.weibo.cn failed.')
        self.save_session()
        self.logger.info('m.weibo.cn Login succeeded.')

    def is_login(self):
        try:
            self.st
            return True
        except LoginException:
            return False

    def save_session(self):
        if self.session_file:
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.session, f)
                self.logger.info(f'Dumped session file to {self.session_file}')

    def load_session(self):
        if self.session_file and os.path.isfile(self.session_file):
            with open(self.session_file, 'rb') as f:
                self.logger.info(f'Loading session from {self.session_file}')
                return pickle.load(f)
        else:
            self.logger.info('Session file does not exist.')
            return requests.Session()

    def upload_pic_multipart(self, pic, pic_name):
        boundary = hex(int(time.time() * 1000))
        encoder = MultipartEncoder([('type', 'json'), ('st', self.st),
                                    # https://github.com/requests/toolbelt/blob/master/requests_toolbelt/multipart/encoder.py#L227
                                    # (file, (file_name, file_pointer, file_type))
                                    ('pic', ('pic', pic, self.guess_content_type(pic_name)))],
                                   boundary)
        headers = copy.deepcopy(WeiboCnApi.COMMON_HEADERS)
        headers.update({'Content-Type': f'multipart/form-data; boundary={boundary}',
                        'X-Requested-With': 'XMLHttpRequest',
                        'MWeibo-Pwa': '1',
                        'Origin': 'https://m.weibo.cn',
                        'Referer': 'https://m.weibo.cn/compose/',
                        'X-XSRF-TOKEN': self.st})
        rsp = self.post(UPLOAD_PIC_URL, headers=headers, data=encoder.to_string(), timeout=self.timeout)
        rsp_data = rsp.json()
        if 'pic_id' not in rsp_data:
            raise RuntimeError('Unknown error when uploading pic %s.', pic_name)
        pic_id = rsp_data['pic_id']
        self.logger.debug('Pic %s is uploaded.', rsp_data['pic_id'])
        return pic_id

    def post_status(self, content, pic_ids=None):
        data = {'content': content, 'st': self.st}
        if pic_ids and len(pic_ids) > 0:
            data['picId'] = ','.join(pic_ids)
        headers = copy.deepcopy(WeiboCnApi.COMMON_HEADERS)
        headers.update({'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest',
                        'MWeibo-Pwa': '1',
                        'Origin': 'https://m.weibo.cn',
                        'Referer': 'https://m.weibo.cn/compose/',
                        'X-XSRF-TOKEN': self.st})
        rsp = self.post(POST_STATUS_URL, headers=headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info('Weibo %s is posted', content)
        else:
            raise RuntimeError('Unknown error posting weibo %s. Response: %s', content, rsp_data)
        return rsp_data

    def repost(self, repost_id, content):
        data = {'id': repost_id, 'mid': repost_id, 'content': content, 'st': self.st}
        headers = copy.deepcopy(WeiboCnApi.COMMON_HEADERS)
        headers.update({'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest',
                        'MWeibo-Pwa': '1',
                        'Origin': 'https://m.weibo.cn',
                        'Referer': 'https://m.weibo.cn/compose/',
                        'X-XSRF-TOKEN': self.st})
        rsp = self.post(REPOST_URL, headers=headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info('Weibo %s:%s is reposted', repost_id, content)
        else:
            raise RuntimeError('Error posting weibo %s:%s. Response: %s', repost_id, content, rsp_data)
        return rsp_data

    def get_pic_id(self, pic_file):
        pic_name = ntpath.basename(pic_file)

        pic_size = os.stat(pic_file).st_size
        if pic_size >= 5000000:  # m.weibo.cn pic upload limitation is 5MB
            with Image.open(pic_file) as pic:
                with BytesIO() as buffer:
                    # save to BytesIO instead of file
                    # https://stackoverflow.com/a/41818645/4214478
                    pic.save(buffer, "JPEG", optimize=True)
                    pic_id = self.upload_pic_multipart(buffer.getvalue(), pic_name)
                    return pic_id
        else:
            with open(pic_file, 'rb') as f:
                pic_id = self.upload_pic_multipart(f, pic_name)
                return pic_id

    @property
    def st(self):
        rsp = self.get(ST_URL, headers=WeiboCnApi.COMMON_HEADERS, timeout=self.timeout).json()
        if not rsp['data']['login']:
            try:
                if self.session_file:
                    os.remove(self.session_file)
            except OSError:
                pass
            raise LoginException('Not logged in.')
        else:
            return rsp['data']['st']

    @staticmethod
    def guess_content_type(url):
        n = url.rfind('.')
        if n == (-1):
            return 'application/octet-stream'
        ext = url[n:]
        return mimetypes.types_map.get(ext, 'application/octet-stream')
