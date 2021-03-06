import os, sys
from argparse import ArgumentParser
from importlib import import_module
from addict import Dict

class ConfigDict(Dict):
    def __missing__(self, name):
        raise KeyError(name)

    def __getattr__(self, name):
        try:
            value = super(ConfigDict, self).__getattr__(name)
        except KeyError:
            ex = AttributeError("'{}' object has no attribute '{}'".format(
                self.__class__.__name__, name))
        except Exception as e:
            ex = e
        else:
            return value
        raise ex

class Config(object):
    """A facility for config and config files.
    It supports common file formats as configs: python/json/yaml. The interface
    is the same as a dict object and also allows access config values as
    attributes.

    Examples
    --------
    >>> cfg = Config(dict(a=1, b=dict(b1=[0, 1])))
    >>> cfg.a
    1
    >>> cfg.b
    {'b1': [0, 1]}
    >>> cfg.b.b1
    [0, 1]
    >>> cfg = Config.fromfile('tests/data/config/a.py')
    >>> cfg.filename
    "/home/kchen/projects/mmcv/tests/data/config/a.py"
    >>> cfg.item4
    'test'
    >>> cfg
    "Config [path: /home/kchen/projects/mmcv/tests/data/config/a.py]: "
    "{'item1': [1, 2], 'item2': {'a': 0}, 'item3': True, 'item4': 'test'}"
    
    References
    ----------
    This code was modified from `the mmcv implementation <https://github.com/open-mmlab/mmcv/blob/5b10dcd79f0f0e9d443c7071c8d798c1a92a6bc5/mmcv/utils/config.py#L49>`_
    """

    @staticmethod
    def fromfile(filename):
        filename = os.path.abspath(os.path.expanduser(filename))
        os.path.exists(filename)
        if filename.endswith('.py'):
            module_name = os.path.basename(filename)[:-3]
            if '.' in module_name:
                raise ValueError('Dots are not allowed in config file path.')
            config_dir = os.path.dirname(filename)
            sys.path.insert(0, config_dir)
            mod = import_module(module_name)
            sys.path.pop(0)
            cfg_dict = {
                name: value
                for name, value in mod.__dict__.items()
                if not name.startswith('__')
            }
        else:
            raise IOError('Only py type is supported now!')
        return Config(cfg_dict, filename=filename)

    def __init__(self, cfg_dict=None, filename=None):
        if cfg_dict is None:
            cfg_dict = dict()
        elif not isinstance(cfg_dict, dict):
            raise TypeError('cfg_dict must be a dict, but got {}'.format(
                type(cfg_dict)))

        super(Config, self).__setattr__('_cfg_dict', ConfigDict(cfg_dict))
        super(Config, self).__setattr__('_filename', filename)
        if filename:
            with open(filename, 'r') as f:
                super(Config, self).__setattr__('_text', f.read())
        else:
            super(Config, self).__setattr__('_text', '')

    @property
    def filename(self):
        return self._filename

    @property
    def text(self):
        return self._text

    def __repr__(self):
        return 'Config (path: {}): {}'.format(self.filename,
                                              self._cfg_dict.__repr__())

    def __len__(self):
        return len(self._cfg_dict)

    def __getattr__(self, name):
        return getattr(self._cfg_dict, name)

    def __getitem__(self, name):
        return self._cfg_dict.__getitem__(name)

    def __setattr__(self, name, value):
        if isinstance(value, dict):
            value = ConfigDict(value)
        self._cfg_dict.__setattr__(name, value)

    def __setitem__(self, name, value):
        if isinstance(value, dict):
            value = ConfigDict(value)
        self._cfg_dict.__setitem__(name, value)

    def __iter__(self):
        return iter(self._cfg_dict)