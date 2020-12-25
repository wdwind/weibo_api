# -*- coding: utf-8 -*-

import base64
import hashlib
import logging
import os
import pickle
import random
import time
from collections import OrderedDict
from os.path import getsize
from urllib.parse import parse_qs, urlparse

from .weibo_com_api_constants import *
from ..exceptions import LoginException
from ..requests_wrapper import RequestsWrapper


class WeiboComApi(RequestsWrapper):
    """weibo.com API for video upload"""

    __COMMON_HEADERS = {
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'http://weibo.com',
        'Referer': 'http://weibo.com/?topnav=1&wvr=6&mod=logo',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/57.0.2987.133 Safari/537.36'
    }

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)

        self.timeout = kwargs.get('timeout', 60)
        self.session = kwargs.get('session', None)
        if self.session is None:
            self.session = self.__load_session(kwargs.get('weibo_session_file', None))
        if self.session is None:
            raise ValueError('session is None. Please provide either a session directly, or a valid session file.')

    def __load_session(self, session_file):
        if session_file and os.path.isfile(session_file):
            with open(session_file, 'rb') as f:
                self.logger.info(f'Loading session from {session_file}')
                return pickle.load(f)

    def __upload_init(self, filename):
        with open(filename, 'rb') as f:
            params = {
                "length": getsize(filename),
                "check": WeiboComApi.__calc_md5(f.read()),
                "type": 'video',
                "source": 2637646381,
                "name": filename,
                'client': 'web',
                'mediaprops': '{"screenshot":0,"video_type":"normal"}',
                "status": 'wired',
                "ua": self.__COMMON_HEADERS['User-Agent'],
                "count": 1
            }
        res = self.post(MULTIMEDIA_INIT_URL, params=params, timeout=self.timeout)
        init_info = res.json()
        if 'error' in init_info:
            raise LoginException(f'Error in video upload initialization. Response: {res.text}')
        return init_info

    def upload_video(self, filename):
        init_info = self.__upload_init(filename)
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
            'sectioncheck': WeiboComApi.__calc_md5(chunk),
            'startloc': start_location,
            'client': 'web',
            'status': 'wired',
            'ua': WeiboComApi.__COMMON_HEADERS['User-Agent'],
            'v': WeiboComApi.__get_unique_key()
        }
        rsp = self.post(MULTIMEDIA_UPLOAD_DATA_URL, params=params, data=chunk, timeout=10 * self.timeout).json()
        try:
            return rsp['succ']
        except:
            try:
                return rsp['fid']
            except:
                return None

    def upload_pic(self, filename):
        params = {
            'cb': f'http://weibo.com/aj/static/upimgback.html?_wv=5&callback=STK_ijax_{WeiboComApi.__get_unique_key()}21',
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
            raise ValueError(f'Video caption must contain at least 6 characters. Caption: {caption}')

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
            ('video_covers', f'http://wx3.sinaimg.cn/large/{pic_id}.jpg|640|360'),
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
                        allow_redirects=True, headers=WeiboComApi.__COMMON_HEADERS)

        try:
            rsp_data = rsp.json()
        except:
            raise LoginException(f'Error posting video {caption}. Response: {rsp.text}')

        if rsp_data['code'] == '100000':
            self.logger.info(f'Weibo {caption} is posted.')
        else:
            self.logger.error(f'Error posting weibo {caption}. Response: {rsp_data}')
        return rsp_data

    @staticmethod
    def __calc_md5(file_content):
        md5obj = hashlib.md5()
        md5obj.update(file_content)
        return md5obj.hexdigest()

    @staticmethod
    def __get_unique_key():
        return str(int(time.time() * 1000)) + str(random.randint(0, 99))
