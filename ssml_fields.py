# -*- coding:utf-8 -*-
from django.db.models import *
from django.conf import settings
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import ValidationError
from django.db.models import Field, CharField

import re

try:
    from hashlib import md5
except ImportError:
    from md5 import new as md5


__all__ = ['SSMLText', 'SSMLTextField']


class SSMLText(object):
    def __init__(self, instance=None, field=None, meta=None, contents=None):
        self._meta = {'n':[], 'a':[], 'e':[]}
        self._contents = {}
        self.field = field
        self.instance = instance
        if meta:
            self.meta = meta
        if contents:
            self.contents = contents

    def _get_meta(self):
        return self._meta

    def _set_meta(self, value):
        self._meta = copy.deepcopy(value)

    def _get_contents(self):
        return self._contents

    def _set_contents(self, value):
        self._contents = copy.deepcopy(value)
        for lang_code in self._contents:
            try:
                self._meta['e'].index(lang_code)
            except:
                self._meta['e'].append(lang_code)

    meta = property(_get_meta, _set_meta)
    contents = property(_get_contents, _set_contents)
        
    def set_meta(self, meta=None, def_lang_code=None, need=None, available=None, exists=None, update_field=True):
        if meta:
            self._meta = copy.deepcopy(meta)
        else:
            if need:
                self._meta['n'] = copy.deepcopy(need)
            if available:
                self._meta['a'] = copy.deepcopy(available)
            if exists:
                self._meta['e'] = copy.deepcopy(exists)
            if def_lang_code:
                self._meta['d'] = copy.deepcopy(def_lang_code)

        if update_field:
            self.update_field(meta=True, contents=False)

    def update_field(self, meta=True, contents=True):
        if self.instance and self.field and meta:
            setattr(self.instance, self.field.meta_field_name, self.field.serialize_meta(self._meta))

        if self.instance and self.field and contents:
            setattr(self.instance, self.field.content_field_name, self.field.serialize_contents(self._contents))

    def add_content(self, code, content, update_field=True):
        self._contents[code] = content
        try:
            self._meta['e'].index(code)
        except:
            self._meta['e'].append(code)

        if update_field:
            self.update_field(meta=True, contents=True)

    def __getitem__(self, key):
        try:
            return self._contents[key]
        except:
            return None

    def __setitem__(self, key, val):
        return self.add_content(key, val)


class SSMLTextFieldCreator(object):
    def __init__(self, field):
        self.field = field

    def _get_cached_instance_or_create(self, instance):
        cached_instance = getattr(instance, self.field.cached_instance_name, None)
        if not cached_instance:
            contents = instance.__dict__[self.field.content_field_name]
            meta = instance.__dict__[self.field.meta_field_name]
            cached_instance = SSMLText(instance, self.field)
            cached_instance.meta = self.field.deserialize_meta(meta)
            cached_instance.contents = self.field.deserialize_contents(contents)

            setattr(instance, self.field.cached_instance_name, cached_instance)

        return cached_instance

    def __get__(self, instance, type=None):  
        if instance is None:  
            raise AttributeError('Can only be accessed via an instance.')  
        return self._get_cached_instance_or_create(instance)

    def __set__(self, instance, value):
        if isinstance(value, SSMLText):
            cached_instance = self._get_cached_instance_or_create(instance)
            cached_instance.meta = value.meta
            cached_instance.contents = value.contents
            cached_instance.update_field()
        else:
            raise AttributeError('Can only be set with SSMLText.')


class SSMLTextField(Field):
    meta_delimeter = '#'

    def __init__(self, *args, **kwargs):
        self.def_lang_code = kwargs.pop('def_lang_code', 'en')

        super(SSMLTextField, self).__init__(*args, **kwargs)

    def serialize_meta(self, meta):
        meta_arr = []
        for m_set_key in meta:
            if isinstance(meta[m_set_key], list):
                for m in meta[m_set_key]:
                    meta_arr.append('%s:%s' % (m_set_key, m))
            else:
                meta_arr.append('%s:%s' % (m_set_key, meta[m_set_key]))
        return '%s%s%s' % (self.meta_delimeter, self.meta_delimeter.join(meta_arr), self.meta_delimeter)

    def serialize_contents(self, contents):
        return json.dumps(contents)

    def deserialize_meta(self, meta):
        delimeter = self.meta_delimeter
        deserialized_meta = {'n':[], 'a':[], 'e':[]}
        for raw_meta in meta.split(delimeter)[1:-1]:
            splitted = raw_meta.split(':')
            if splitted[0] in ['n', 'a', 'e']:
                deserialized_meta[splitted[0]].append(splitted[1])
        if not deserialized_meta.get('d', None):
            deserialized_meta['d'] = self.def_lang_code

        return deserialized_meta

    def deserialize_contents(self, contents):
        return json.loads(contents)

    def contribute_to_class(self, cls, name):
        self.name = name
        self.meta_field_name = "%s_meta" % (self.name,)
        self.content_field_name = "%s_content" % (self.name,)
        self.cached_instance_name = '%s_cached_instance'% (self.name)

        self.content_field = TextField(default=u'{}')
        self.content_field.creation_counter = self.creation_counter
        self.meta_field = CharField(max_length=2014, default='%sd:%s%s' % (self.meta_delimeter, self.def_lang_code, self.meta_delimeter))
        self.meta_field.creation_counter = self.creation_counter

        cls.add_to_class(self.content_field_name, self.content_field)
        cls.add_to_class(self.meta_field_name, self.meta_field)

        setattr(cls, self.name, SSMLTextFieldCreator(self))



