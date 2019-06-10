import os

try:
    from simple_captcha.weibo_com_captcha import WeiboComCaptcha
except ImportError:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from simple_captcha.weibo_com_captcha import WeiboComCaptcha


if __name__ == '__main__':
    weibo_captcha = WeiboComCaptcha()
    filename = 'zyene.png'
    with open(filename, 'rb') as f:
        label = weibo_captcha.predict(f.read())
        print(format('Predicted label for %s is %s' % (filename, label)))
