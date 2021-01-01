# Weibo Write API

A Python wrapper for Weibo write API.

![Python 3.7](https://img.shields.io/badge/Python-3.7-3776ab.svg?maxAge=2592000)

## Note (202012)

Weibo(.com/.cn) recently had an update, which added more restrictions to the login logic. Basically if a device is not trusted, by default a secondary verification is required for login. We have accommodated with this change, and now the api supports secondary verification via sms or private message. 

Although secondary verification is supported, there are some non-negligible limitations. For example, the process cannot be fully automated (need human intervention), and the sms verification can only be used a few times per day. 

As a result, it is highly recommended to save the requests session to avoid re-login every time when using the api. Check [``examples/``](examples/) on how to save/load the session to a file. 

## Features

* Login with private message or sms
* Post text
* Post image
* **Post video**
* Repost

## Install

* Install with pip:
  ```
  pip install git+https://git@github.com/wdwind/weibo_api.git
  ```

* To update:
  ```
  pip install git+https://git@github.com/wdwind/weibo_api.git --upgrade
  ```

* To update with latest repo code:
  ```
  pip install git+https://git@github.com/wdwind/weibo_api.git --upgrade --force-reinstall
  ```

## Examples

Check [``examples/``](examples/). 

## Development

* Run unit tests
  ```
  python -m unittest discover
  ```

## License

MIT

## Disclaimer

Weibo services are highly unstable. Use it at your own risk.
