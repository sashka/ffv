# -*- coding: utf-8 -*_
import re
import json
from collections import defaultdict

class Form(object):

    def __init__(self, schema, data):
        self.schema = schema
        self.data = data
        self.validators = _builtin_validators
        self.preporcessors = _builtin_preprocessors
        self.errors = {}

    def add_to_schema(self, schema):
        dd = defaultdict(list)
        for d in (self.schema, schema):
            for key, value in d.iteritems():
                dd[key] += value
        self.schema = dd

    def add_validator(self, name, callback):
        if callable(callback):
            self.validators[name] = callback

    def add_preprocessor(self, name, callback):
        if callable(callback):
            self.preporcessors[name] = callback


    def preprocess(self):
        if 'preprocess' not in self.schema or not self.schema['preprocess']:
            return None
        for element_pattern , func_name in self.schema['preprocess'].items():
            is_list = False
            if func_name.startswith('list:'):
                is_list = True
                func_name = func_name.split(':', 1)[1]
            if func_name not in self.preporcessors:
                continue
            func = self.preporcessors[func_name]
            items = self.getItems(self.data, element_pattern)
            for key, value in items.items():
                if isinstance(value, list):
                    if is_list:
                        self.data[key] = map(func, value)
                    elif len(value) > 0:
                        self.data[key] = func(value[0])
                    else:
                        del self.data[key] # fix me !!!
                else:
                    self.data[key] = func(value)

    def process_validator(self, validator):
        validator_name = validator.get('name', None)

        if validator_name == 'rule':
            result = self.applayRule(validator)
            self.logic_stack.append(result)
            return True
        elif validator_name == 'block':
            if not validator.get('rules', None):
                return False
            logic = validator.get('logic', 'and')
            if logic == 'if' and len(validator['rules']) not in (2,3):
                return False
            applay_rules = 0
            for rule in validator['rules']:
                res = self.process_validator(rule)
                if res:
                    applay_rules += 1
            if applay_rules:
                block_logic = self.logic_stack[-applay_rules:]
                _tmp =len(self.logic_stack) - applay_rules
                self.logic_stack = self.logic_stack[: -_tmp]
                result = self.applyLogic(logic, block_logic)
                if  validator.get('inverted','no') == 'yes':
                    result = not result
                self.logic_stack.append(result)
                return True
        return False

    def validate(self):
        if 'validate' not in self.schema or not self.schema['validate']:
            return True
        self.preprocess()
        self.logic_stack = []
        self.errors = {}
        for validator in self.schema['validate']:
            self.process_validator(validator)

        if self.logic_stack:
            return self.applyLogic('and', self.logic_stack)
        else:
            return True



    def getItems(self, data, pattern):
        items = {}
        for key in data:
            if re.match(pattern, key):
                items[key] = data[key]
        return items

    def applayRule(self, rule):
        rule_type = rule.get('type', 'require')
        if rule_type not in self.validators:
            return True
        applay_to = []
        items =  {}
        for_elements = rule.get('for', None)
        if not for_elements:
            items = self.data
        else:
            if  isinstance(rule.get('for'), list):
                applay_to = for_elements
            else:
                applay_to = [for_elements]
        if applay_to:
            for el in applay_to:
                items.update(self.getItems(self.data, el) or {el:''})
        error_items  = self.validators[rule_type](items, rule)
        self.onError(error_items, rule.get('onerror', None), rule.get('errtarget', None))
        result = False if error_items else True
        if rule.get('inverted','no') == 'yes':
            result = not result
        return result

    def onError(self, items, onerror, errtarget):
        for item in items:
            err = errtarget or item
            if err not in self.errors:
                self.errors[err] = onerror

    def applyLogic(self, logic_type, values):
        if logic_type == 'or':
            return any(values)
        elif logic_type == 'and':
            return all(values)
        elif logic_type == 'if':
            if len(values) == 3:
                return values[0] and values[1] or values[2]
            else:
                return values[0] and values[1] or True
        False

    def errorsJson(self, indent=None):
        return json.dumps(self.errors, indent=indent)

    def dataJson(self, indent=None):
        return json.dumps(self.data, indent=indent)

    def schemaJson(self, indent=None):
        return json.dumps(self.schema, indent=indent)


### buildin preprocess

def parseint(value):
    try:
        return int(value)
    except ValueError:
        return 0

def pasefloat(value):
    try:
        return float(value)
    except ValueError:
        return 0.0

def trim(value):
    return value.strip()

def normalize(value):
    trim(value)
    return re.sub(r'[^\S\r\n]+', ' ', value, flags=re.MULTILINE)

def nospace(value):
    return value.replace(' ','')

def uppercase(value):
    return value.uppercase()

def lowercase(value):
    return value.lowercase()

_builtin_preprocessors = {
    'int': parseint,
    'float': pasefloat,
    'trim': trim,
    'bool': bool,
    'normalize': normalize,
    'nospace': nospace,
    'uppercase': uppercase,
    'lowercase': lowercase,
    }

### validators
def require_validator(values, rule):
    error_items = []
    for key, value in values.items():
        if not value:
            error_items.append(key)
    return error_items

def eq_validator(values, rule):
    error_items = []
    _tmp = values.items()
    for i in _tmp:
        if i+1 > len(_tmp):
            break
        if _tmp[i][1] != _tmp[i+1][1]:
            error_items.append(_tmp[i+1][0])
            break
    return error_items

def regexp_validator(values, rule):
    error_items = []
    if not rule.get('pattern', None):
        return error_items
    for key, value in values.items():
        if not re.match(rule.get('pattern'), value):
            error_items.append(key)
    return error_items

def len_validator(values, rule):
    error_items = []
    _min = rule.get('min', None)
    _max = rule.get('max', None)
    if not _min or not _max:
        return error_items
    for key, value in values.items():
        value = value[0]
        if _min and len(value) < int(_min):
            error_items.append(key)
            continue
        if _max and len(value) > int(_max):
            error_items.append(key)
    return error_items

_builtin_validators = {
    'require': require_validator,
    'eq': eq_validator,
    'regexp': regexp_validator,
    'len': len_validator,
    }

