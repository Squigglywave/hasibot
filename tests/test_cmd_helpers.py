import sys
sys.path.append("..")
import pytest
from config import DB_URL, SCHEMA_NAME
from utils import DataConnector, DataProcessor

class guilds():
    def __init__(self):
        self.id = '775944111463202846' 

def setup_module(module):
    DataConnector.create_engine(DB_URL)

def test_on_ready():
    guild_id = '775944111463202846'
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,guild_id))

    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,guild_id))

    assert df.shape[0] == 0

    obj_guild = guilds()
    
    lst_guilds = []
    lst_guilds.append(obj_guild)

    DataProcessor._on_ready(lst_guilds)

    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,guild_id))

    assert df.shape[0] == 1
