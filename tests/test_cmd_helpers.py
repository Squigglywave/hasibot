import sys
sys.path.append("..")
import pytest
from config import DB_URL, SCHEMA_NAME
from utils import DataConnector, DataProcessor

# import discord
# 
# intents = discord.Intents.all()
# intents.members = True
# client = discord.Client(intents=intents)

class guilds():
    def __init__(self):
        self.id = '775944111463202846'

@pytest.fixture(scope="module")
def gid():
    return '775944111463202846'

def setup_module(module):
    DataConnector.create_engine(DB_URL)

@pytest.mark.ready
def test_on_ready(gid):
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))

    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))

    assert df.shape[0] == 0

    obj_guild = guilds()
    
    lst_guilds = []
    lst_guilds.append(obj_guild)

    DataProcessor._on_ready(lst_guilds)

    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))

    assert df.shape[0] == 1

@pytest.mark.join
def test_on_guild_join(gid):
    # Make sure guild is removed from guilds table
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

    # Make sure guild is removed from days table
    DataConnector.run_query("DELETE FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

    obj_guild = guilds()

    # Check on guild join
    DataProcessor._on_guild_join(obj_guild)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    # Also very the days table
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    # Check that the size doesn't change on the same guild
    DataProcessor._on_guild_join(obj_guild)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

@pytest.mark.remove
def test_on_guild_remove(gid):
    # Ensure that size 1
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    obj_guild = guilds()

    # Remove the guild and verify none in guilds and days tables
    DataProcessor._on_guild_remove(obj_guild)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

@pytest.mark.add_react
def test_on_raw_reaction_add():
    pass


@pytest.mark.watch_ch
def test_on_message_watch_channel(gid):
    cid = '1234567890'
    DataProcessor._on_message_watch_channel(gid, cid)
    df = DataConnector.read_data("SELECT channel_id FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df['channel_id'][0] == cid
