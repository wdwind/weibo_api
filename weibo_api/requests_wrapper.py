# -*- coding: utf-8 -*-

import logging

import requests
from requests_toolbelt.utils import dump


class RequestsWrapper(object):
    session = requests.session()
    logger = logging.getLogger(__name__)

    def get(self, *args, **kwargs):
        rsp = self.session.get(*args, **kwargs)
        data = dump.dump_all(rsp)
        try:
            # python 2
            # self.logger.debug(unicode(bytes(data), errors='ignore'))
            # python 3
            # py3 uses system default EOL (end of line) character
            # In windows, it is \r\n, and the dumped data has characters '\r\n', and it will
            # automatically changed to \r\r\n when writing to the file.
            # So we need call an additional replace to fix the problem.
            data_str = str(bytes(data), encoding='utf-8', errors='ignore').replace('\r\n', '\n')
            self.logger.debug(data_str)
        except:
            self.logger.debug(data)
        return rsp

    def post(self, *args, **kwargs):
        rsp = self.session.post(*args, **kwargs)
        data = dump.dump_all(rsp)
        try:
            # python 2
            # self.logger.debug(unicode(bytes(data), errors='ignore'))
            # python 3
            data_str = str(bytes(data), encoding='utf-8', errors='ignore').replace('\r\n', '\n')
            self.logger.debug(data_str)
        except:
            self.logger.debug(data)
        return rsp
