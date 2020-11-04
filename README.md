# Weibo Write API

A Python wrapper for Weibo write API.

![Python 3.7](https://img.shields.io/badge/Python-3.7-3776ab.svg?maxAge=2592000)

## Features

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

### Avoiding Re-login

The recommendation is to save the request session to avoid logging in every time when initiating the class. Too many logins will result in a security check which is not supported by the current lib. 

## Development

* Run unit tests
  ```
  python -m unittest discover
  ```

## License

MIT

## Disclaimer

Weibo services are highly unstable. Use it at your own risk.
