# -*- coding: utf-8 -*-

import requests

from weibo_api.simple_captcha.weibo_com_captcha import WeiboComCaptcha


def local_image():
    weibo_captcha = WeiboComCaptcha()
    filename = 'zyene.png'
    with open(filename, 'rb') as f:
        label = weibo_captcha.predict(f.read())
        print('Predicted label for %s is %s' % (filename, label))


def online_image():
    weibo_captcha = WeiboComCaptcha(data_path='./', save_captcha=True)
    pic = requests.get('http://login.sina.com.cn/cgi/pin.php')
    pin = weibo_captcha.predict(pic.content)
    print('Predicted label: %s' % pin)


if __name__ == '__main__':
    local_image()
    # online_image()
