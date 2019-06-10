import json
import unittest

from weibo_cn_api.weibo_cn_api import WeiboCnApi
from weibo_cn_api.weibo_cn_api_constants import *

try:
    from unittest.mock import MagicMock, patch, mock_open
except ImportError:  # Python 2
    from mock import MagicMock, patch, mock_open


class WeiboCnApiTest(unittest.TestCase):

    def setUp(self):
        self.config = {'login_user': 'username',
                       'login_password': 'password'}
        request_mock = MagicMock(side_effect=self.mock_response)
        WeiboCnApi.post = request_mock
        WeiboCnApi.get = request_mock

    def tearDown(self):
        pass

    # https://stackoverflow.com/questions/16162015/mocking-python-function-based-on-input-arguments
    @staticmethod
    def mock_response(arg, **kwargs):
        response = MagicMock()
        if arg == M_WEIBO_CN_LOGIN_URL:
            response.content = '{"retcode":20000000,"msg":"","data":{"crossdomainlist":{"weibo.com":"..","sina.com.cn":"..","weibo.cn":".."},"loginresulturl":"","uid":".."}}'
            return response
        elif arg == ST_URL:
            response.content = '{"preferQuickapp":0,"data":{"login":true,"st":"a32bc4","uid":"5711920318"},"ok":1}'
            return response
        elif arg == UPLOAD_PIC_URL:
            response.content = '{"pic_id":"pic_id","thumbnail_pic":"thumbnail_pic","bmiddle_pic":"bmiddle_pic","original_pic":"original_pic"}'
            response.json.return_value = json.loads(response.content)
            return response
        elif arg == POST_STATUS_URL or arg == REPOST_URL:
            response.content = '{"ok":1,"data":{}}'
            response.json.return_value = json.loads(response.content)
            return response

    def test_login(self):
        WeiboCnApi(**self.config)

    def test_login_no_username(self):
        self.config.pop('login_password')
        with self.assertRaises(RuntimeError):
            WeiboCnApi(**self.config)

    def test_login_no_password(self):
        self.config.pop('login_user')
        with self.assertRaises(RuntimeError):
            WeiboCnApi(**self.config)

    @patch('weibo_cn_api.weibo_cn_api.MultipartEncoder')
    def test_upload_pic_multipart(self, mock_multipart_encoder):
        mock_img_bytes = MagicMock()
        mock_img_bytes.to_string.return_value = 'img_bytes'
        mock_multipart_encoder.return_value = mock_img_bytes

        weibo = WeiboCnApi(**self.config)
        self.assertEqual(weibo.upload_pic_multipart('pic', 'pic_name'), 'pic_id')

    def test_post_status(self):
        weibo = WeiboCnApi(**self.config)
        response = weibo.post_status('content', 'img')
        self.assertEqual(response, {"ok": 1, "data": {}})

    def test_repost(self):
        weibo = WeiboCnApi(**self.config)
        response = weibo.repost('repost_id', 'content')
        self.assertEqual(response, {"ok": 1, "data": {}})

    @patch('weibo_cn_api.weibo_cn_api.MultipartEncoder')
    def test_post_status_pic_files(self, mock_multipart_encoder):
        mock_img_bytes = MagicMock()
        mock_img_bytes.to_string.return_value = 'img_bytes'
        mock_multipart_encoder.return_value = mock_img_bytes

        weibo = WeiboCnApi(**self.config)
        with patch('weibo_cn_api.weibo_cn_api.open', mock_open(read_data=b'data')) as m:
            response = weibo.post_status_pic_files('a', ['b'])

        self.assertEqual(response, {"ok": 1, "data": {}})
