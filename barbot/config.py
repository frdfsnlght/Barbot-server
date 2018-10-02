
import os, configparser

from . import paths


config = None


def load():
    global config
    config = configparser.ConfigParser(
        interpolation = None,
        converters = {
            'path': resolvePath
        }
    )
    config.optionxform = str    # preserve option case
    config.read(os.path.join(paths.ETC_DIR, 'config-default.ini'))
    config.read(os.path.join(paths.ETC_DIR, 'config.ini'))
    return config

def resolvePath(str):
    str = str.replace('!root', paths.ROOT_DIR)
    str = str.replace('!bin', paths.BIN_DIR)
    str = str.replace('!etc', paths.ETC_DIR)
    str = str.replace('!var', paths.VAR_DIR)
    str = str.replace('!content', paths.CONTENT_DIR)
    return str
        