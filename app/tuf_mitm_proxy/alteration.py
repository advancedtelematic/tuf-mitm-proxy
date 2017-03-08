# -*- coding: utf-8 -*-no

import base64
import binascii
import ed25519
import json
import os
import random
import rsa

from canonicaljson import encode_canonical_json
from os import path


class Alteration:
    '''Base class for HTTP alterations'''

    @classmethod
    def check(cls, resp):  # pragma: no cover
        '''Check if an alteration can be applied to a response'''
        raise NotImplemented

    @classmethod
    def apply(cls, resp):  # pragma: no cover
        '''Apply an alteration to a response'''
        raise NotImplemented

    @classmethod
    def _is_json(cls, resp):
        return resp.headers.get('Content-Type') == 'application/json'

    @classmethod
    def _is_signed_json(cls, resp):
        '''Checks if the JSON is of the form:
           ```{"signatures":[
               ...
               ],
               ...
               "signed": ...,
               ...
               }
              
           ```
        '''
        if cls._is_json(resp):
            # TODO this is defnitely just insane and should never happen, yet somehow here I am
            if not hasattr(resp, 'data'):
                resp.data = resp.text.encode('utf-8')

            # TODO data might not be utf-8 encoded
            jsn = json.loads(resp.data.decode('utf-8'))
            return 'signatures' in jsn and 'signed' in jsn
        else:
            return False

    @staticmethod
    def _get_key_material(typ='rsa', num=1, private=True):
        root = path.join(path.dirname(__file__), '../keys')

        if typ == 'rsa':
            if private:
                key_suffix = '_{}.pem'.format(num)
            else:
                key_suffix = '_{}.pub.pem'.format(num)

            with open(path.join(root, (typ + key_suffix)), 'r') as f:
                return f.read()
        elif typ == 'ed25519':
            if private:
                key_suffix = '_{}'.format(num)
            else:
                key_suffix = '_{}.pub'.format(num)

            with open(path.join(root, (typ + key_suffix)), 'rb') as f:
                return base64.b64decode(f.read())
        else:  # pragma: no cover
            raise ValueError('Key type not supported')


class NoOpAlteration(Alteration):
    '''The "default" case that does not alter the response at all.'''

    NAME = 'no-op'

    @classmethod
    def check(cls, resp):
        '''Never valid.'''
        return False

    @classmethod
    def apply(cls, resp):
        return resp


class TwiddleJson(Alteration):
    '''Makes exactly one arbitrary change to the JSON body of response'''

    NAME = 'twiddle-json'

    @classmethod
    def check(cls, resp):
        return cls._is_json(resp)

    @classmethod
    def apply(cls, resp):
        # TODO might not always be utf-8
        body = resp.data.decode('utf-8')
        jsn = cls._twiddle_json(json.loads(body))
        resp.data = encode_canonical_json(jsn)
        return resp

    @classmethod
    def _twiddle_json(cls, jsn):
        if isinstance(jsn, dict):
            jsn = jsn.copy()
            if jsn:
                for key, value in jsn.items():
                    jsn[key] = cls._twiddle_json(value)
                    break
            else:
                jsn = {'password': 'hunter2'}
        elif isinstance(jsn, list):
            jsn = jsn.copy()
            if jsn:
                jsn[0] = cls._twiddle_json(jsn[0])
            else:
                jsn.append('wat')
        elif isinstance(jsn, bool):
            jsn = not jsn
        elif isinstance(jsn, str):
            jsn = jsn + '1337 h4x'
        elif isinstance(jsn, float) or isinstance(jsn, int):
            jsn = jsn + 1
        else:
            jsn = 'wat'
        return jsn


class AddSignatures(Alteration):
    '''Adds signatures to responses with signed JSON bodies'''

    NAME = 'add-sigantures-1'
    ADDITIONS = 1

    @classmethod
    def check(cls, resp):
        return cls._is_signed_json(resp)

    @classmethod
    def apply(cls, resp):
        jsn = json.loads(resp.data.decode('utf-8'))

        # create a list of all possible key options
        key_opts = []
        for key_num in range(1,7):
            for is_rsa in (True, False):
                key_opts.append({'key_num': key_num, 'is_rsa': is_rsa})

        # randomize the list
        key_opts = list(sorted(key_opts, key=lambda x: random.random()))

        for x in range(0, cls.ADDITIONS):
            # use the randomly selected items (selection without replacement)
            sig = cls._sign_json(jsn, **key_opts[x])
            jsn['signatures'].insert(0, sig)

        resp.data = encode_canonical_json(jsn)
        return resp

    @classmethod
    def _sign_json(cls, jsn, is_rsa, key_num):
        signable = encode_canonical_json(jsn['signed'])

        if is_rsa:
            priv = cls._get_key_material('rsa', key_num)
            method = 'RSASSA-PSS'
            # TODO check that this is correct
            sig = rsa.sign(signable, rsa.PrivateKey.load_pkcs1(priv, 'PEM'), 'SHA-256')
        else:
            priv = cls._get_key_material('ed25519', key_num)
            method = 'ed25519'
            sig = ed25519.SigningKey(priv).sign(signable, encoding='base64')
        
        return {'method': method,
                'keyid': binascii.hexlify(os.urandom(32)).decode('utf-8'),  # TODO
                'sig': base64.b64encode(sig).decode('utf-8')}


class AddSignatures2(AddSignatures):

    NAME = 'add-signatures-2'
    ADDITIONS = 2


class AddSignatures3(AddSignatures):

    NAME = 'add-signatures-3'
    ADDITIONS = 3


class DeleteSignatures(Alteration):
    '''Removes signatures from responses with signed JSON bodies'''

    NAME = 'delete-signatures-1'
    DELETIONS = 1 

    @classmethod
    def check(cls, resp):
        return cls._is_signed_json(resp)

    @classmethod
    def apply(cls, resp):
        # TODO data might not be utf-8 encoded
        jsn = json.loads(resp.data.decode('utf-8'))
        jsn['signatures'] = jsn['signatures'][cls.DELETIONS:]
        resp.data = encode_canonical_json(jsn)
        return resp


class DeleteSignatures2(DeleteSignatures):

    NAME = 'delete-signatures-2'
    DELETIONS = 2


class DeleteSignatures3(DeleteSignatures):

    NAME = 'delete-signatures-3'
    DELETIONS = 3


class DuplicateSignature(Alteration):

    NAME = 'duplicate-signatures'

    @classmethod
    def check(cls, resp):
        return cls._is_signed_json(resp)

    @classmethod
    def apply(cls, resp):
        jsn = json.loads(resp.data.decode('utf-8'))
        jsn['signatures'].insert(0, jsn['signatures'][0].copy())
        resp.data = encode_canonical_json(jsn)
        return resp


# TODO flip chars in existing signatures


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in all_subclasses(s)]


available_alterations = all_subclasses(Alteration)


def select_alteration(resp, choices=None):
    '''Randomly select one alteration to apply to the HTTP response'''

    alterations = list(filter(lambda x: x.NAME in choices and x.check(resp),
                       available_alterations))

    if not alterations:
        alterations = [NoOpAlteration]

    return random.choice(alterations)
