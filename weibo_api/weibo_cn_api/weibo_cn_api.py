# -*- coding: utf-8 -*-

import copy
import logging
import mimetypes
import os
import pickle
import time
from io import BytesIO

from PIL import Image
from requests_toolbelt import MultipartEncoder

from .weibo_cn_api_constants import *
from ..exceptions import LoginException
from ..requests_wrapper import RequestsWrapper


class WeiboCnApi(RequestsWrapper):
    """m.weibo.cn API"""

    __COMMON_HEADERS = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36',
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

    def __upload_pic_multipart(self, pic, pic_file):
        boundary = hex(int(time.time() * 1000))
        encoder = MultipartEncoder([('type', 'json'), ('st', self.__st),
                                    # https://github.com/requests/toolbelt/blob/master/requests_toolbelt/multipart/encoder.py#L227
                                    # (file, (file_name, file_pointer, file_type))
                                    ('pic', ('pic', pic, self.__guess_content_type(pic_file)))],
                                   boundary)
        headers = copy.deepcopy(WeiboCnApi.__COMMON_HEADERS)
        headers.update({
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'X-Requested-With': 'XMLHttpRequest',
            'MWeibo-Pwa': '1',
            'Origin': 'https://m.weibo.cn',
            'Referer': 'https://m.weibo.cn/compose/',
            'X-XSRF-TOKEN': self.__st
        })
        rsp = self.post(UPLOAD_PIC_URL, headers=headers, data=encoder.to_string(), timeout=self.timeout)
        rsp_data = rsp.json()
        if 'pic_id' not in rsp_data:
            raise RuntimeError(f'Unknown error when uploading pic {pic_file}')
        pic_id = rsp_data['pic_id']
        self.logger.debug(f'Pic {rsp_data["pic_id"]} is uploaded.')
        return pic_id

    def post_status(self, content, pic_ids=None):
        data = {'content': content, 'st': self.__st}
        if pic_ids and len(pic_ids) > 0:
            data['picId'] = ','.join(pic_ids)
        headers = copy.deepcopy(WeiboCnApi.__COMMON_HEADERS)
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'MWeibo-Pwa': '1',
            'Origin': 'https://m.weibo.cn',
            'Referer': 'https://m.weibo.cn/compose/',
            'X-XSRF-TOKEN': self.__st
        })
        rsp = self.post(POST_STATUS_URL, headers=headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info(f'Weibo {content} is posted.')
        else:
            raise RuntimeError(f'Unknown error posting weibo {content}. Response: {rsp_data}')
        return rsp_data

    def repost(self, repost_id, content):
        data = {'id': repost_id, 'mid': repost_id, 'content': content, 'st': self.__st}
        headers = copy.deepcopy(WeiboCnApi.__COMMON_HEADERS)
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Requested-With': 'XMLHttpRequest',
            'MWeibo-Pwa': '1',
            'Origin': 'https://m.weibo.cn',
            'Referer': 'https://m.weibo.cn/compose/',
            'X-XSRF-TOKEN': self.__st
        })
        rsp = self.post(REPOST_URL, headers=headers, data=data, timeout=self.timeout)
        rsp_data = rsp.json()
        if rsp_data['ok'] == 1:
            self.logger.info(f'Weibo {repost_id}:{content} is reposted.')
        else:
            raise RuntimeError(f'Error posting weibo {repost_id}:{content}. Response: {rsp_data}')
        return rsp_data

    def get_pic_id(self, pic_file):
        pic_size = os.stat(pic_file).st_size
        if pic_size >= 5000000:  # m.weibo.cn pic upload limitation is 5MB
            with Image.open(pic_file) as pic:
                with BytesIO() as buffer:
                    # save to BytesIO instead of file
                    # https://stackoverflow.com/a/41818645/4214478
                    pic.save(buffer, 'JPEG', optimize=True)
                    pic_id = self.__upload_pic_multipart(buffer.getvalue(), pic_file)
                    return pic_id
        else:
            with open(pic_file, 'rb') as f:
                pic_id = self.__upload_pic_multipart(f, pic_file)
                return pic_id

    @property
    def __st(self):
        rsp = self.get(ST_URL, headers=WeiboCnApi.__COMMON_HEADERS, timeout=self.timeout).json()
        if not rsp['data']['login']:
            raise LoginException('Login required.')
        else:
            return rsp['data']['st']

    @staticmethod
    def __guess_content_type(url):
        n = url.rfind('.')
        if n == (-1):
            return 'application/octet-stream'
        ext = url[n:]
        return mimetypes.types_map.get(ext, 'application/octet-stream')
