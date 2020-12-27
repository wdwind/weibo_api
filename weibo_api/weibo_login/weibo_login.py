import base64
import binascii
import copy
import json
import logging
import os
import pickle
import random
import re
import time
from urllib.parse import quote, parse_qs, urlparse, unquote

import requests
import rsa

from ..exceptions import LoginException
from ..requests_wrapper import RequestsWrapper
from ..simple_captcha.weibo_com_captcha import WeiboComCaptcha


class WeiboLoginApi(RequestsWrapper):

    __SUPPORTED_VERIFICATION_TYPE = ['private_msg', 'sms']

    __COMMON_HEADERS = {
        # 'Accept': '*/*',
        # 'Accept-Encoding': 'gzip, deflate, br',
        # 'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.6',
        # 'User-Agent': 'Mozilla/5.0 (Linux; Android 7.0; SM-G892A Build/NRD90M; wv) AppleWebKit/537.36 '
        #               '(KHTML, like Gecko) Version/4.0 Chrome/67.0.3396.87 Mobile Safari/537.36',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/57.0.2987.133 Safari/537.36'
    }

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(__name__)

        self.login_user = kwargs.get('login_user', None)
        self.login_password = kwargs.get('login_password', None)
        if not self.login_user or not self.login_password:
            raise ValueError('Username and password has to be provided.')

        self.verification_type = kwargs.get('verification_type', 'private_msg')
        if self.verification_type not in self.__SUPPORTED_VERIFICATION_TYPE:
            raise ValueError(f'Unsupported secondary verification type. '
                             f'Supported types are: {self.__SUPPORTED_VERIFICATION_TYPE}')

        self.captcha_cracker = WeiboComCaptcha(save_captcha=kwargs.get('save_captcha', False))
        self.timeout = kwargs.get('timeout', 60)
        self.session_file = kwargs.get('weibo_session_file', None)
        self.session = self.__load_session()

    ##########################################################################################
    # weibo.com login
    ##########################################################################################
    def weibo_com_login(self):
        prelogin_data = self.__weibo_com_prelogin()
        ajax_login_url = 'https://www.weibo.com/ajaxlogin.php?framelogin=1&callback=parent.sinaSSOController.feedBackUrlCallBack'
        payload = {
            'cdule': 2,
            'domain': 'weibo.com',
            'encoding': 'UTF-8',
            'entry': 'weibo',
            'from': '',
            'gateway': 1,
            'nonce': prelogin_data.get('nonce', ''),
            'pagerefer': 'http://login.sina.com.cn/sso/logout.php?entry=miniblog&r=http%3A%2F%2Fweibo.com%2Flogout.php%3Fbackurl%3D%252F',
            'prelt': 236,
            'pwencode': 'rsa2',
            'qrcode_flag': False,
            'returntype': 'TEXT',
            'rsakv': prelogin_data.get('rsakv', ''),
            'savestate': 7,
            'servertime': prelogin_data.get('servertime', ''),
            'service': 'miniblog',
            'sp': self.__encrypted_pwd(prelogin_data),
            'sr': '1280*720',
            'su': self.__su,
            'url': ajax_login_url,
            'useticket': 1,
            'vsnf': 1,
        }

        if prelogin_data.get('showpin', 0) == 1:
            payload.update({
                'door': prelogin_data['pin'],
                'cdult': 2,
                'pcid': prelogin_data['pcid'],
                'prelt': 2041
            })

        login_data = self.post('https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)', data=payload).json()
        if login_data['retcode'] == '0':
            self.__weibo_com_sso(ajax_login_url, login_data['ticket'])
        elif login_data['retcode'] == '2071' and login_data['reason'] == u'请使用扫码登录':
            self.logger.info('Weibo.com secondary verification required.')
            protection_url = unquote(login_data['protection_url'])
            redirect_url = self.__weibo_com_secondary_verification(protection_url)
            self.__weibo_com_cross_domain_login(redirect_url)
        elif login_data['retcode'] == '2070' and login_data['reason'] == u'输入的验证码不正确':
            self.logger.error(f'Wrong captcha: {prelogin_data.get("pin", None)}. Reporting...')
            self.captcha_cracker.report_wrong_result(prelogin_data.get("pin", None))
            raise LoginException(f'Login failed. Data: {json.dumps(login_data)}')
        else:
            raise LoginException(f'Login failed. Data: {json.dumps(login_data)}')

        self.__weibo_com_cn_auth()
        self.__save_session()
        self.logger.info('Weibo login succeeded!')

    def __weibo_com_prelogin(self):
        params = {
            '_': int(time.time() * 1000),
            'callback': 'sinaSSOController.preloginCallBack',
            'checkpin': 1,
            'client': 'ssologin.js(v1.4.19)',
            'entry': 'weibo',
            'rsakt': 'mod',
            'su': self.__su
        }
        headers = copy.deepcopy(self.__COMMON_HEADERS)
        headers.update({'Referer': 'https://weibo.com/'})
        response = self.get('https://login.sina.com.cn/sso/prelogin.php', params=params, headers=headers)
        prelogin_data = json.loads(re.findall(r'preloginCallBack\(([\w\W]+?)\)', response.text)[0])
        if prelogin_data.get('showpin', 0) == 1:
            prelogin_data['pin'] = self.__get_pin(prelogin_data['pcid'])
        return prelogin_data

    def __get_pin(self, pcid):
        params = {
            'p': pcid,
            'r': random.randint(10000, 100000),
            's': 0
        }
        pic = self.get('http://login.sina.com.cn/cgi/pin.php', params=params)
        pin = self.captcha_cracker.predict(pic.content)
        self.logger.info('Weibo.com captcha: %s', pin)
        return pin

    def __weibo_com_sso(self, ajax_login_url, ticket):
        self.get('https://i.sso.sina.com.cn/js/ssologin.js')
        params = {
            'callback': 'sinaSSOController.doCrossDomainCallBack',
            'client': 'ssologin.js(v1.4.19)',
            'display': 0,
            'ticket': ticket,
            'retcode': 0,
            'ssosavestate': 7,
            'url': ajax_login_url + '&sudaref=www.weibo.com',
        }
        self.get('http://passport.weibo.com/wbsso/login', params=params)
        self.get(ajax_login_url + '&sudaref=www.weibo.com')
        # interest = self.get('http://weibo.com/nguide/interest', timeout=self.timeout)
        # uid = re.search(r"CONFIG\['uid'\]='([^']+)'", interest.text).group(1)
        # nick = re.search(r"CONFIG\['nick'\]='([^']+)'", interest.text).group(1)

    def __weibo_com_secondary_verification(self, protection_url):
        token = parse_qs(urlparse(protection_url).query)['token'][0]
        if self.verification_type == 'sms':
            check_data = self.__weibo_com_sms_verification(protection_url, token)
        elif self.verification_type == 'private_msg':
            check_data = self.__weibo_com_private_msg_verification(token)
        else:
            raise ValueError('verification_type can only be sms or private_msg')

        if str(check_data['retcode']) != '20000000':
            raise LoginException(f'Secondary verification failed. Data: {json.dumps(check_data)}')

        return check_data['data']['redirect_url']

    def __weibo_com_sms_verification(self, protection_url, token):
        protection_page = self.get(protection_url)
        encrypted_mobile = re.search(r'value="([^"]+)" class="W_radio"', protection_page.text).group(1)
        params = {'token': token}
        payload = {'encrypt_mobile': encrypted_mobile}
        send_code = self.post('https://passport.weibo.com/protection/mobile/sendcode', params=params, data=payload).json()
        if send_code['retcode'] != 20000000:
            raise LoginException('Exceeds mobile verification limit.')
        code = input('Please input the verification code you received through sms: ')
        payload.update({'code': code})
        return self.get('https://passport.weibo.com/protection/mobile/confirm', params=params, data=payload).json()

    def __weibo_com_private_msg_verification(self, token):
        payload = {'token': token}
        self.post('https://passport.weibo.com/protection/privatemsg/send', data=payload)
        while True:
            confirm = input('Type "confirm" to make sure you approved the login request in private message, '
                            'or type "cancel" to cancel the login: ')
            if confirm == 'confirm':
                break
            elif confirm == 'cancel':
                raise LoginException('User canceled the login.')
        return self.post('https://passport.weibo.com/protection/privatemsg/getstatus', data=payload).json()

    def __weibo_com_cross_domain_login(self, redirect_url):
        redirect_response = self.get(redirect_url)
        cross_domain_url = re.search(r'location.replace\("([^"]+)"\);', redirect_response.text).group(1)
        cross_domain_response = self.get(cross_domain_url)
        domains = json.loads(re.search(r'setCrossDomainUrlList\(([\w\W]+?)\)', cross_domain_response.text).group(1))['arrURL']
        for domain_url in domains:
            try:
                self.get(domain_url)
            except Exception as e:
                self.logger.warning(f'Unable to finish cross domain authentication for {domain_url}', e)
        login_url = re.search(r'location.replace\(\'([^\']+)\'\)', cross_domain_response.text).group(1)
        self.get(login_url, allow_redirects=True)

    def __weibo_com_cn_auth(self):
        root = self.get('https://weibo.cn/')
        cross_domain_url = re.search(r'location.replace\("([^"]+)"\);', root.text).group(1)
        cross_domain_response = self.get(cross_domain_url)
        domains = json.loads(re.search(r'setCrossDomainUrlList\(([\w\W]+?)\)', cross_domain_response.text).group(1))['arrURL']
        for domain_url in domains:
            self.get(domain_url)
        cross_domain_login_url = re.search(r'location.replace\(\'([^\']+)\'\)', cross_domain_response.text).group(1)
        self.get(cross_domain_login_url, allow_redirects=True)

    ##########################################################################################
    # weibo.cn login
    ##########################################################################################
    def weibo_cn_login(self):
        sso_headers = copy.deepcopy(self.__COMMON_HEADERS)
        sso_headers.update({
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://passport.sina.cn',
            'Referer': 'https://passport.sina.cn/signin/signin',
        })
        payload = {
            'username': self.login_user,
            'password': self.login_password,
            'savestate': 1,
            'ec': 1,
            'pagerefer': '',
            'entry': 'wapsso',
            'sinacnlogin': 1,
        }
        sso_response = self.post('https://passport.sina.cn/sso/login', headers=sso_headers, data=payload).json()

        if sso_response['retcode'] == 50050011:
            self.logger.info('Weibo.cn secondary verification required.')
            self.__weibo_cn_secondary_verification(sso_response['data']['errurl'])
        elif sso_response['retcode'] == 20000000:
            login_result_url = sso_response['data']['loginresulturl'] + '&savestate=1&url=https://sina.cn'
            self.get(login_result_url)
            self.get('https://sina.cn')
            self.get('https://m.weibo.cn/?vt=4&pos=108')
        else:
            raise LoginException('Login to m.weibo.cn failed.')

        self.__save_session()
        self.logger.info('Weibo login succeeded!')

    def __weibo_cn_secondary_verification(self, verification_page_url):
        verification_page = self.get(verification_page_url)
        send_code_params = {'msg_type': self.verification_type}
        if self.verification_type == 'sms':
            mobile = json.loads(re.search(r'phoneList: JSON.parse\(\'([^\']+)\'\),', verification_page.text).group(1))
            send_code_params.update({
                'number': mobile[0]['number'],
                'mask_mobile': mobile[0]['maskMobile'],
                'msg_type': self.verification_type,
            })
        elif self.verification_type == 'private_msg':
            self.get('https://passport.weibo.cn/signin/secondverify/index', params={'way': self.verification_type})
        else:
            raise ValueError('verification_type can only be sms or private_msg')

        send_code_data = self.get('https://passport.weibo.cn/signin/secondverify/ajsend', params=send_code_params).json()
        if send_code_data['retcode'] != 100000:
            raise LoginException(f'Unable to send verification code. Server response: {json.dumps(send_code_data)}')

        code = input(f'Please input the verification code you got from {self.verification_type}: ')
        check_code_params = {
            'msg_type': self.verification_type,
            'code': code,
        }
        check_code_data = self.get('https://passport.weibo.cn/signin/secondverify/ajcheck', params=check_code_params).json()
        if check_code_data['retcode'] == 100000:
            login_url = check_code_data['data']['url']
            self.get(login_url)
        else:
            raise LoginException(f'Secondary verification error. Response: {json.dumps(check_code_data)}')

    ##########################################################################################
    # Utilities
    ##########################################################################################
    def __save_session(self):
        if self.session_file:
            with open(self.session_file, 'wb') as f:
                pickle.dump(self.session, f)
                self.logger.info(f'Dumped session file to {self.session_file}')

    def __load_session(self):
        if self.session_file and os.path.isfile(self.session_file):
            with open(self.session_file, 'rb') as f:
                self.logger.info(f'Loading session from {self.session_file}')
                return pickle.load(f)
        else:
            self.logger.info('Session file does not exist.')
            return requests.Session()

    def is_cn_login(self):
        response_json = self.get('https://m.weibo.cn/api/config').json()
        return response_json['data']['login']

    def is_com_login(self):
        response = self.get('https://weibo.com/', headers=self.__COMMON_HEADERS)
        return u'uid' in response.text

    def get(self, *args, **kwargs):
        default_kwargs = {
            'headers': self.__COMMON_HEADERS,
            'timeout': self.timeout,
        }
        default_kwargs.update(**kwargs)
        return super().get(*args, **default_kwargs)

    def post(self, *args, **kwargs):
        default_kwargs = {
            'headers': self.__COMMON_HEADERS,
            'timeout': self.timeout,
        }
        default_kwargs.update(**kwargs)
        return super().post(*args, **default_kwargs)

    def __encrypted_pwd(self, prelogin_data):
        """
        Get encrypted password
        """
        pubkey = int(prelogin_data.get('pubkey', ''), 16)
        rsa_key = rsa.PublicKey(pubkey, 65537)  # Create public key
        secret = str(prelogin_data.get('servertime', '')) + '\t' + \
                 str(prelogin_data.get('nonce', '')) + '\n' + str(self.login_password)
        pwd = rsa.encrypt(secret.encode('utf-8'), rsa_key)  # Encrypt with RSA
        return binascii.b2a_hex(pwd)  # Convert encrypted data to HEX

    @property
    def __su(self):
        """
        Get encoded username
        """
        return base64.encodebytes(quote(self.login_user).encode('utf-8'))[:-1]
