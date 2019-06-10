# Weibo Write API

A Python wrapper for Weibo write API.

![Python 2.7, 3.6](https://img.shields.io/badge/Python-2.7%2C%203.6-3776ab.svg?maxAge=2592000)

## Features

* Post text
* Post image
* **Post video**
* Repost

## Install

Install with pip:

``pip install git+https://git@github.com/wdwind/weibo_api.git``

To update:

``pip install git+https://git@github.com/wdwind/weibo_api.git --upgrade``

To update with latest repo code:

``pip install git+https://git@github.com/wdwind/weibo_api.git --upgrade --force-reinstall``

Tested on Python 2.7 and 3.6.

## Examples

Check [``examples/``](examples/).

### Avoiding Re-login

The recommendation is to save the cookies for `m.weibo.cn` to avoid logging in every time when initiating the class. Too many logins in will result in a security check with no-captcha, which currently isn't supported by this library. 

For `weibo.com`, the cookies don't work for now. A mitigation is to save the requests session directly, which requires some tweaks on the source code.

## License

MIT

## Disclaimer

Use at your own risk.
