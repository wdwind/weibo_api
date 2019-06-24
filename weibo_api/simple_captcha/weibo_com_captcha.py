# -*- coding: utf-8 -*-

import logging
import os
import pickle
import time
from io import BytesIO

import mxnet as mx
import numpy as np
from PIL import Image
from mxnet import gluon, nd


class WeiboComCaptcha(object):
    """Weibo.com captcha recognition."""

    CURRENT_DIR = os.path.dirname(__file__)
    INPUT_SHAPE = (100, 40)

    def __init__(self, index_path='model/index.pkl',
                 model_symbol_path='model/0.9269662921348315.net.all-symbol.json',
                 model_params_path='model/0.9269662921348315.net.all-0001.params',
                 data_path='./data', save_captcha=False):
        self.data_path = os.path.join(data_path)
        self.save_captcha = save_captcha
        if save_captcha and not os.path.exists(self.data_path):
            os.makedirs(self.data_path)
        self.index2ch, self.ch2index = self.read_index(os.path.join(self.CURRENT_DIR, index_path))
        self.net = self.read_model(os.path.join(self.CURRENT_DIR, model_symbol_path),
                                   os.path.join(self.CURRENT_DIR, model_params_path))

    def predict(self, im_bytes):
        im = raw_im = Image.open(BytesIO(im_bytes))
        if self.INPUT_SHAPE != raw_im.size:
            logging.error('Invalid image shape %s!', str(raw_im.size))
            im = raw_im.resize(self.INPUT_SHAPE)
        data = np.asarray(im, dtype=np.float32)
        data = data.reshape(-1, 1, self.INPUT_SHAPE[1], self.INPUT_SHAPE[0])
        out = self.net(self.transform(nd.array(data).as_in_context(mx.cpu())))
        predictions = nd.argmax(out, axis=2)
        predicted_label = ''.join([self.index2ch[i] for i in predictions[0].asnumpy()])
        if self.save_captcha:
            self.save_im(raw_im, predicted_label)
        return predicted_label

    def save_im(self, im, label):
        im_name = label + '_' + str(int(time.time())) + '.png'
        im.save(os.path.join(self.data_path, im_name))

    def report_wrong_result(self, predicted_label):
        if self.save_captcha:
            files = os.listdir(self.data_path)
            for file_name in files:
                if predicted_label in file_name:
                    old_file = os.path.join(self.data_path, file_name)
                    new_file = os.path.join(self.data_path, 'wrong_' + file_name)
                    os.rename(old_file, new_file)
                    return
            logging.error('Image file not found!')

    @staticmethod
    def read_model(model_symbol_path, model_params_path):
        return gluon.nn.SymbolBlock.imports(model_symbol_path, ['data'], model_params_path)

    @staticmethod
    def read_index(path):
        with open(path, 'rb') as f:
            index_dict = pickle.load(f)

        return index_dict['index2ch'], index_dict['ch2index']

    @staticmethod
    def transform(image):
        """
        This function resizes the input image and converts so that it could be fed into the network.
        """
        image = image / 255.
        image = (image - 0.942532484060557) / 0.15926149044640417
        return image
