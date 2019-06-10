# -*- coding: utf-8 -*-

import copy
import http.cookiejar
import json
import logging
import mimetypes
import ntpath
import os
import time
import traceback

import pickledb
import requests
from requests import ConnectionError
from requests_toolbelt import MultipartEncoder

from ..util.decorator import retries
from ..util.requests_wrapper import RequestsWrapper
from .weibo_cn_api_constants import *


class WeiboCnApi(RequestsWrapper):
    """m.weibo.cn API"""

    headers = {'Accept': 'application/json, text/plain, */*',
               'Accept-Encoding': 'gzip, deflate, br',
               'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.6,en;q=0.4',
               'Connection': 'keep-alive',
               'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
               'X-Requested-With': 'XMLHttpRequest',
               'Host': 'm.weibo.cn',
               'Origin': 'https://m.weibo.cn',
               'Referer': 'https://m.weibo.cn/compose'}

    def __init__(self, **kwargs):
        self.login_user = kwargs.get('login_user', None)
        self.login_password = kwargs.get('login_password', None)

        self.logger = logging.getLogger(__name__)

        # Pic cache pickledb
        pic_cache = kwargs.get('pic_cache', None)
        if pic_cache and os.path.isfile(pic_cache):
            self.cache = pickledb.load(pic_cache, False)
        else:
            self.cache = None

        self.timeout = kwargs.get('timeout', 60)
        self.session = requests.Session()
        self.session.headers = WeiboCnApi.headers
        self.cookie_file = kwargs.get('cookie_file', None)

        if self.cookie_file and os.path.isfile(self.cookie_file):
            self.session.cookies = http.cookiejar.LWPCookieJar(self.cookie_file)
            self.session.cookies.load(ignore_expires=True)
        else:
            if not self.login_user or not self.login_password:
                raise RuntimeError('Login required.')
            self.login()

    def login(self):
        """Login m.weibo.cn. token is not needed here."""
        headers = copy.deepcopy(self.headers)
        headers.update({'Content-Type': 'application/x-www-form-urlencoded',
                        'Host': 'passport.weibo.cn',
                        'Origin': 'https://passport.weibo.cn',
                        'Referer': M_WEIBO_CN_REFERER_URL})
        form_data = {
            'username': self.login_user,
            'password': self.login_password,
            'savestate': 1,
            'r': 'http://m.weibo.cn/',
            'ec': 0,
            'pagerefer': M_WEIBO_CN_PAGE_REFERER_URL,
            'entry': 'mweibo',
            'mainpageflag': 1
        }
        response = self.post(M_WEIBO_CN_LOGIN_URL, headers=headers, data=form_data, timeout=self.timeout)
        response_data = json.loads(response.content)
        if response_data['retcode'] != 20000000:
            raise RuntimeError('Login m.weibo.cn failed.')
        if self.cookie_file:
            self.session.cookies.save(filename=self.cookie_file, ignore_discard=True, ignore_expires=True)
        self.logger.info('m.weibo.cn Login succeeded.')

    def upload_pic_multipart(self, pic, pic_name):
        boundary = hex(int(time.time() * 1000))
        encoder = MultipartEncoder([('type', 'json'), ('st', self.st),
                                    # https://github.com/requests/toolbelt/blob/master/requests_toolbelt/multipart/encoder.py#L227
                                    # (file, (file_name, file_pointer, file_type))
                                    ('pic', ('pic', pic, self.guess_content_type(pic_name)))],
                                   boundary)
        headers = copy.deepcopy(self.headers)
        headers.update({'Content-Type': 'multipart/form-data; boundary={}'.format(boundary)})
        rsp = self.post(UPLOAD_PIC_URL, headers=headers, data=encoder.to_string(), timeout=self.timeout)
        rsp_data = rsp.json()
        if 'pic_id' not in rsp_data:
            self.login()
            raise ConnectionError('Unknown error when uploading pic %s.', pic_name)
        pic_id = rsp_data['pic_id']
        self.logger.debug('Pic %s is uploaded.', rsp_data['pic_id'])
        return pic_id

    def post_status(self, content, pic_ids=None):
        data = {'content': content, 'st': self.st}
        if pic_ids and len(pic_ids) > 0:
            data['picId'] = ','.join(pic_ids)
        rsp = self.post(POST_STATUS_URL, headers=self.headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info('Weibo %s is posted', content)
        else:
            self.login()
            raise ConnectionError('Unknown error posting weibo %s. Response: %s', content, rsp_data)
        return rsp_data

    def repost(self, repost_id, content):
        data = {'id': repost_id, 'mid': repost_id, 'content': content, 'st': self.st}
        rsp = self.post(REPOST_URL, headers=self.headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info('Weibo %s:%s is reposted', repost_id, content)
        else:
            self.login()
            raise ConnectionError('Error posting weibo %s:%s. Response: %s', repost_id, content, rsp_data)
        return rsp_data

    @retries(max_tries=3, delay=60,
             hook=lambda tries_remaining, exception, delay:
             logging.getLogger(__name__)
             .error(u'Exception when posting to weibo.cn. %s: %s. %d tries remaining. Sleeping for %s seconds.'
                    % (exception, traceback.format_exc(), tries_remaining, delay)))
    def post_status_pic_files(self, content, pic_files):
        pics = []

        for pic_file in pic_files:
            pics.append(self.get_pic_id(pic_file))

        return self.post_status(content, pics)

    def get_pic_id(self, pic_file):
        pic_name = ntpath.basename(pic_file)

        if self.cache and self.cache.get(pic_name):
            cached_id = self.cache.get(pic_name)
            self.logger.info('Cache hit for %s. Value: %s', pic_name, cached_id)
            return cached_id
        else:
            with open(pic_file, 'rb') as f:
                pic_id = self.upload_pic_multipart(f, pic_name)
                if self.cache:
                    self.cache.set(str(pic_name), pic_id)
                    self.cache.dump()
                return pic_id

    @property
    def st(self):
        rsp = self.get(ST_URL, headers=self.headers, timeout=self.timeout).json()
        if not rsp['data']['login']:
            self.login()
            return self.st
        else:
            return rsp['data']['st']

    @staticmethod
    def guess_content_type(url):
        n = url.rfind('.')
        if n == (-1):
            return 'application/octet-stream'
        ext = url[n:]
        return mimetypes.types_map.get(ext, 'application/octet-stream')
