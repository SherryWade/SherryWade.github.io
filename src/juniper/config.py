import configparser
import os

# TODO: Upgrade this and set it from an env variable
USER_HOME = os.path.expanduser('~')
JUNIPER_HOME = os.path.join(USER_HOME, 'GitHub', 'bsethwalker', 'charlestonmysteries')

# Data Directories
DATA_DIR = os.path.join(JUNIPER_HOME, 'data')

EXTERNAL_DATA_DIR = os.path.join(DATA_DIR, 'external')
INTERIM_DATA_DIR = os.path.join(DATA_DIR, 'interim')
