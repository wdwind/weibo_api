import json
import unittest

from weibo_api import WeiboComApi
from weibo_api.weibo_com_api.weibo_com_api_constants import *

try:
    from unittest.mock import MagicMock, patch, mock_open
except ImportError:  # Python 2
    from mock import MagicMock, patch, mock_open


class WeiboComApiTest(unittest.TestCase):

    PATH = 'weibo_api.weibo_com_api.weibo_com_api'

    def setUp(self):
        self.config = {'login_user': 'username',
                       'login_password': 'password'}
        request_mock = MagicMock(side_effect=self.mock_response)
        WeiboComApi.post = request_mock
        WeiboComApi.get = request_mock

    def tearDown(self):
        pass

    # https://stackoverflow.com/questions/16162015/mocking-python-function-based-on-input-arguments
    @staticmethod
    def mock_response(arg, **kwargs):
        response = MagicMock()
        if arg == LOGIN_URL:
            response.content = '{"retcode":"0","ticket":"ticket","uid":"uid","nick":"random"}'
            response.json.return_value = json.loads(response.content)
            return response
        elif arg == PRELOGIN_URL:
            response.content = 'sinaSSOController.preloginCallBack({"retcode":0,"servertime":1,"pcid":"pcid","nonce":"1","pubkey":"EB2A38568661887FA180BDDB5CABD5F21C7BFD59C090CB2D245A87AC2530628","rsakv":"1","is_openlock":0,"showpin":0,"exectime":40})'
            response.text = response.content
            return response
        elif arg == SSO_LOGIN_URL:
            response.content = ''
            return response
        elif arg == LOGIN_PASSPORT:
            response.content = ''
            return response
        elif arg == LOGIN_PARAMS_URL_WITH_REF:
            response.content = ''
            return response
        elif arg == MULTIMEDIA_INIT_URL:
            response.content = '{"fileToken":"59062","urlTag":"1","length":512,"threads":2,"idc":"ali"}'
            return response
        elif arg == MULTIMEDIA_UPLOAD_DATA_URL:
            response.content = '{"fid":"1","fmid":"1","media_id":"1","biz_id":"1","url":"http://f.us.sinaimg.cn/1"}'
            response.json.return_value = json.loads(response.content)
            return response
        elif arg == MULTIMEDIA_UPLOAD_PIC_URL:
            response.url = 'http://weibo.com/aj/static/upimgback.html?_wv=5&callback=ajax&ret=1&pid=pid'
            return response
        elif arg == POST_WEIBO_URL:
            response.content = '{"code":"100000","msg":"","data":{"html":"html"}}'
            response.json.return_value = json.loads(response.content)
            return response

    def test_login(self):
        WeiboComApi(**self.config)

    def test_login_no_username(self):
        self.config.pop('login_password')
        with self.assertRaises(RuntimeError):
            WeiboComApi(**self.config)

    def test_login_no_password(self):
        self.config.pop('login_user')
        with self.assertRaises(RuntimeError):
            WeiboComApi(**self.config)

    @patch(PATH + '.getsize')
    def test_upload_video(self, mock_getsize):
        mock_getsize.return_value = 1

        weibo = WeiboComApi(**self.config)
        with patch(self.PATH + '.open', mock_open(read_data=b'data')) as m:
            fid = weibo.upload_video('video.mp4')
            self.assertEqual(fid, '1')

    def test_get_media_id(self):
        weibo = WeiboComApi(**self.config)
        with patch(self.PATH + '.open', mock_open(read_data=b'data')) as m:
            pid = weibo.get_media_id('pic.png', weibo.upload_pic)
            self.assertEqual(pid, 'pid')

    @patch(PATH + '.WeiboComApi.get_media_id')
    @patch(PATH + '.WeiboComApi.upload_video')
    def test_post_weibo(self, mock_upload_video, mock_get_media_id):
        mock_upload_video.return_value = 'fid'
        mock_get_media_id.return_value = 'pid'

        weibo = WeiboComApi(**self.config)
        with patch(self.PATH + '.open', mock_open(read_data=b'data')) as m:
            response = weibo.post_weibo('caption', 'video.mp4', 'pic.png')
            self.assertEqual(response, {"code": "100000", "msg": "", "data": {"html": "html"}})
