import sys
sys.path.append("..")
import pytest
from config import DB_URL, SCHEMA_NAME
from utils import DataConnector, DataProcessor

class guilds():
    def __init__(self, id='12345'):
        self.id = id

@pytest.fixture(scope="module")
def gid():
    return '12345'

@pytest.fixture(scope="module")
def obj_guild():
    obj_guild = guilds()
    return obj_guild

def setup_module(module):
    DataConnector.create_engine(DB_URL)

@pytest.mark.ready
def test_on_ready(gid,obj_guild):
    # New guild test
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

    lst_guilds = []
    lst_guilds.append(obj_guild)

    DataProcessor._on_ready(lst_guilds)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    # Same guild list test 
    DataProcessor._on_ready(lst_guilds)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1

    # Additional guild test
    new_gid='54321'
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,new_gid))
    new_obj_guild = guilds(new_gid)
    lst_guilds.append(new_obj_guild)
    DataProcessor._on_ready(lst_guilds)
    df = DataConnector.read_data("""SELECT *
                                    FROM {}.guilds
                                    WHERE guild_id='{}' or guild_id='{}'
                                 """.format(SCHEMA_NAME,gid,new_gid))
    assert df.shape[0] == 2

    # Removed guilds test
    empty_lst_guilds = []
    DataProcessor._on_ready(empty_lst_guilds)
    df = DataConnector.read_data("""SELECT *
                                    FROM {}.guilds
                                    WHERE guild_id='{}' or guild_id='{}'
                                 """.format(SCHEMA_NAME,gid,new_gid))
    assert df.shape[0] == 0

    # One last sanity check
    lst_guilds.remove(new_obj_guild)
    DataProcessor._on_ready(lst_guilds)
    df = DataConnector.read_data("""SELECT *
                                    FROM {}.guilds
                                    WHERE guild_id='{}' or guild_id='{}'
                                 """.format(SCHEMA_NAME,gid,new_gid))
    assert df.shape[0] == 1


@pytest.mark.join
def test_on_guild_join(gid,obj_guild):
    # Make sure guild is removed from guilds table
    DataConnector.run_query("DELETE FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

    # Make sure guild is removed from days table
    DataConnector.run_query("DELETE FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

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
def test_on_guild_remove(gid,obj_guild):
    DataProcessor._on_guild_join(obj_guild)

    # Ensure that size 1
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 1


    # Remove the guild and verify none in guilds and days tables
    DataProcessor._on_guild_remove(obj_guild)
    df = DataConnector.read_data("SELECT * FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0
    df = DataConnector.read_data("SELECT * FROM {}.days WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df.shape[0] == 0

    DataProcessor._on_guild_join(obj_guild)

@pytest.mark.add_react
def test_on_raw_reaction_add():
    pass


@pytest.mark.watch_ch
def test_on_message_watch_channel(gid,obj_guild):
    DataProcessor._on_guild_join(obj_guild)

    cid = '1234567890'
    DataProcessor._on_message_watch_channel(gid, cid)
    df = DataConnector.read_data("SELECT channel_id FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df['channel_id'][0] == cid

    DataProcessor._on_guild_join(obj_guild)


@pytest.mark.watch_msg
def test_on_message_watch_message(gid,obj_guild):
    DataProcessor._on_guild_join(obj_guild)

    mid = '1234567890'
    DataProcessor._on_message_watch_message(gid,mid)
    df = DataConnector.read_data("SELECT message_id FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df['message_id'][0] == mid

    df = DataConnector.read_data("SELECT COUNT(*) FROM {}.guilds WHERE guild_id='{}'".format(SCHEMA_NAME,gid))
    assert df['count'][0] == 1
    
    DataProcessor._on_guild_join(obj_guild)
