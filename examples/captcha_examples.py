# -*- coding: utf-8 -*-

from weibo_api.simple_captcha.weibo_com_captcha import WeiboComCaptcha


if __name__ == '__main__':
    weibo_captcha = WeiboComCaptcha()
    filename = 'zyene.png'
    with open(filename, 'rb') as f:
        label = weibo_captcha.predict(f.read())
        print(format('Predicted label for %s is %s' % (filename, label)))
