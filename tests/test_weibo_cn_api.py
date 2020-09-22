import json
import unittest

from weibo_api import WeiboCnApi
from weibo_api.weibo_cn_api.weibo_cn_api import LoginException
from weibo_api.weibo_cn_api.weibo_cn_api_constants import *

try:
    from unittest.mock import MagicMock, PropertyMock, patch, mock_open
except ImportError:  # Python 2
    from mock import MagicMock, PropertyMock, patch, mock_open


class WeiboCnApiTest(unittest.TestCase):

    PATH = 'weibo_api.weibo_cn_api.weibo_cn_api'

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
        elif arg == ST_URL:
            response.content = '{"preferQuickapp":0,"data":{"login":true,"st":"a32bc4","uid":"5711920318"},"ok":1}'
        elif arg == UPLOAD_PIC_URL:
            response.content = '{"pic_id":"pic_id","thumbnail_pic":"thumbnail_pic","bmiddle_pic":"bmiddle_pic","original_pic":"original_pic"}'
        elif arg == POST_STATUS_URL or arg == REPOST_URL:
            response.content = '{"ok":1,"data":{}}'

        response.json.return_value = json.loads(response.content)
        return response

    def test_login(self):
        WeiboCnApi(**self.config)

    def test_login_no_username(self):
        def st(arg, **kwargs):
            response = MagicMock()
            response.content = '{"preferQuickapp":0,"data":{"login":false,"st":"a32bc4","uid":"5711920318"},"ok":1}'
            response.json.return_value = json.loads(response.content)
            return response
        request_mock = MagicMock(side_effect=st)
        WeiboCnApi.get = request_mock
        self.config.pop('login_password')
        with self.assertRaises(RuntimeError):
            WeiboCnApi(**self.config)

    def test_login_no_password(self):
        def st(arg, **kwargs):
            response = MagicMock()
            response.content = '{"preferQuickapp":0,"data":{"login":false,"st":"a32bc4","uid":"5711920318"},"ok":1}'
            response.json.return_value = json.loads(response.content)
            return response
        request_mock = MagicMock(side_effect=st)
        WeiboCnApi.get = request_mock
        self.config.pop('login_user')
        with self.assertRaises(RuntimeError):
            WeiboCnApi(**self.config)

    @patch(PATH + '.MultipartEncoder')
    def test_upload_pic_multipart(self, mock_multipart_encoder):
        mock_img_bytes = MagicMock()
        mock_img_bytes.to_string.return_value = 'img_bytes'
        mock_multipart_encoder.return_value = mock_img_bytes

        weibo = WeiboCnApi(**self.config)
        self.assertEqual(weibo.upload_pic_multipart('pic', 'pic_name'), 'pic_id')

    @patch('os.stat')
    @patch(PATH + '.MultipartEncoder')
    def test_get_pic_id(self, mock_multipart_encoder, mock_stat):
        mock_img_bytes = MagicMock()
        mock_img_bytes.to_string.return_value = 'img_bytes'
        mock_multipart_encoder.return_value = mock_img_bytes

        mock_file_size = MagicMock()
        type(mock_file_size).st_size = PropertyMock(return_value=1)
        mock_stat.return_value = mock_file_size

        weibo = WeiboCnApi(**self.config)
        with patch(self.PATH + '.open', mock_open(read_data=b'data')) as m:
            response = weibo.get_pic_id('b')

        self.assertEqual(response, 'pic_id')

    def test_post_status(self):
        weibo = WeiboCnApi(**self.config)
        response = weibo.post_status('content', 'img')
        self.assertEqual(response, {"ok": 1, "data": {}})

    def test_repost(self):
        weibo = WeiboCnApi(**self.config)
        response = weibo.repost('repost_id', 'content')
        self.assertEqual(response, {"ok": 1, "data": {}})


if __name__ == '__main__':
    unittest.main()
