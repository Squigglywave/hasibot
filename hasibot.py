# Standard Library
import os
import io
import xml.etree.ElementTree as ET
import datetime

# Third Party Library
import requests
import discord
from dotenv import load_dotenv
import pandas as pd

# Application Specific Library
from utils import get_echo_30, get_boosted_echo_30, DataConnector
from config import lst_scols, time_zone

# Loads environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')      # Bot token
ENVIRONMENT = os.getenv('ENVIRONMENT')
DB_URL = os.getenv('DATABASE_URL')

# Load different variables based on environment
if ENVIRONMENT == 'DEV':
    SCHEMA_NAME = 'hasibot_dev'
elif ENVIRONMENT == 'PROD':
    SCHEMA_NAME = 'hasibot'

# Intents used to track guild member lists
intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)

###########
# Globals #
###########
# List of acceptable day emoji names; Discord server needs to name the emojis in
# this exact format
day_emotes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

##################
# Helper Methods #
##################
def day_print(guild_id, lst_users):
    '''
    Generates a numbered list of names.

    Arguments:
    - guild_id    string  the ID of the guild to fetch the guild members from
    - lst_users   list    an ordered list of user IDs (strings)

    Returns:
    - ret_str     string  numbered list of nicknames or discord usernames
    '''
    ret_str = ""

    for n, user_id in enumerate(lst_users):
        user = client.get_guild(int(guild_id)).get_member(int(user_id))
        if user.nick is not None:
            name = user.nick
        else:
            name = user.name
        ret_str = ret_str + "    " + str(n+1) + ". " + name + "\n"

    return ret_str

def grab_day(df, day):
    '''
    Generates a list of user IDs based on the given day.

    Arguments:
    - df    Pandas DataFrame  dataframe containing the user IDs and days reacted
    - day   string            which day to get a list of user IDs

    Returns:
    - lst_day   list  a list of strings of the user IDs, empty list of no user IDs
    '''

    # Use try/except block for non-existent day errors in the dataframe
    try:
        lst_day = df.groupby('day')['user_id'].unique()[day]
    except Exception as ex:
        lst_day = []
    return lst_day

###################
# Discord Methods #
###################
@client.event
async def on_ready():
    '''
    Executes when the Discord bot first starts.
    - Retrieves a list of guilds currently in the DB
    - Checks if any guilds this bot currently is active in are not in the DB
    - If non-existent, creates an entry in the DB for the guild
    '''
    # Create the DB connection on start up
    DataConnector.create_engine(DB_URL)

#TODO: consider appending and not truncating and then appending
    df_all_guilds = pd.DataFrame()
    df = DataConnector.read_data('SELECT * FROM {}.guilds'.format(SCHEMA_NAME))
    df_all_guilds = pd.concat([df_all_guilds,df])
    async for guild in client.fetch_guilds(limit=150):
        if str(guild.id) not in df_all_guilds['guild_id'].tolist():
            dict_guild = {'guild_id':str(guild.id), 'channel_id':'','message_id':''}
            df_guild = pd.DataFrame([dict_guild])
            df_all_guilds = pd.concat([df_all_guilds,df_guild])

    DataConnector.run_query("TRUNCATE TABLE {}.guilds".format(SCHEMA_NAME))
    DataConnector.write_data(df_all_guilds, SCHEMA_NAME,'guilds', 'append')
    print("Bot is ready!")

@client.event
async def on_guild_join(guild):
    '''
    Executes when the Discord bot joins a guild.
    - Inserts the supplied guild ID into the guilds table
    - Inserts a dummy value into the days table for print_info

    Arguments:
    - guild   int   the guild ID
    '''
    # This query checks if an entry already exists before inserting into the table.
    # If the entry exists, nothing is done.
    query = open("data/guild_join_query.txt").read().format(SCHEMA_NAME, str(guild.id))
    DataConnector.run_query(query)

@client.event
async def on_guild_remove(guild):
    '''
    Executes when the Discord bot leaves or is removed from a guild.
    - Removes the given guild ID from the guilds table
    - Removes all entries from the days table with a matching guild id

    Arguments
    - guild   int   the guild ID
    '''
    # This query removes the guild ID from the guilds table and removes all
    # entries with that same guild ID
    DataConnector.run_query(("""DELETE FROM {0}.guilds
                                WHERE guild_id = '{1}';
                                DELETE FROM {0}.days
                                WHERE guild_id = '{1}';
                             """).format(SCHEMA_NAME, str(guild.id)))

@client.event
async def on_raw_reaction_add(payload):
    '''
    Executes when a reaction in a guild is added.
    - Returns if the guild's watched channel and message have not been set
    - Returns if the payload's message id is not the one being watched
    - On new reacts to the watched message, add the user ID that reacted to a
      queue for the reacted day

    Arguments:
    - payload   RawReactionActionEvent  a Discord object
    '''
#TODO: improvements like calling the query after simple early return checks?
#      is channel needed?
    global day_emotes
    guild_id = str(payload.guild_id)

    # Run query to get the channel and message IDs for the requesting guild
    df_channel = DataConnector.read_data(("""SELECT message_id, channel_id
                                             FROM {0}.guilds
                                             WHERE guild_id = '{1}'
                                          """).format(SCHEMA_NAME, guild_id))
    channel = client.get_channel(int(df_channel['channel_id'][0]))
    message_id = df_channel['message_id'][0]

    if (channel is None) or (message_id == ''):
        return

    # Check if the reactions are on the watched message
    if payload.message_id == int(message_id):
        # Get the reaction and insert an entry into the days table if the
        # reaction is valid.
        day = str(payload.emoji.name)
        if day in day_emotes:
            now = datetime.datetime.now(time_zone).strftime("%Y-%m-%d_%H:%M:%S.%f")
            dict_val = {'guild_id':guild_id, 'day':str(day), 'user_id':str(payload.member.id), 'insert_ts':now}
            df_val = pd.DataFrame([dict_val])
            DataConnector.write_data(df_val, SCHEMA_NAME, 'days')

@client.event
async def on_raw_reaction_remove(payload):
    '''
    Executes when a reaction in a guild is removed.
    - Returns if the guild's watched channel and message have not been set
    - Returns if the payload's message id is not the one being watched
    - On unreacts to the watched message, remove the user ID that unreacted from
      the queue for the unreacted day

    Arguments:
    - payload   RawReactionActionEvent  a Discord object
    '''
#TODO: improvements like calling the query after simple early return checks?
#      is channel needed?
    global day_emotes
    guild_id = str(payload.guild_id)

    # Run query to get the channel and message IDs for the requesting guild
    df_channel = DataConnector.read_data(("""SELECT message_id, channel_id
                                             FROM {0}.guilds
                                             WHERE guild_id = '{1}'
                                          """).format(SCHEMA_NAME, guild_id))
    channel = client.get_channel(int(df_channel['channel_id'][0]))
    message_id = df_channel['message_id'][0]

    if (channel is None) or (message_id == ''):
        return

    # Check if the unreact occurred to the watched message
    if payload.message_id == int(message_id):
        # Convert the payload's user ID and emote to a string and remove the
        # user ID on that emote day from the days table
        user = str(payload.user_id)
        day = str(payload.emoji.name)

        # Run another query to delete a user if they unreacted
        DataConnector.run_query(("""DELETE FROM {0}.days
                                    WHERE user_id = '{1}' AND 
                                          day = '{2}'
                                 """).format(SCHEMA_NAME, user, day))

@client.event
async def on_message(message):
    '''
    Parses through all messages in the discord server.
    - Early exit if the message does not start with the correct prefix
    - Watches for the following commands (not case sensitive):
      > watch_channel
      > watch_message
      > hasi
      > roll_echo
      > roll_boosted_echo
      > print_info
      > search items
      > search es

    Arguments:
    - message   Message   a Discord object
    '''
    global day_emotes
    guild_id = str(message.guild.id)

    # Quick optimization as this bot is watching all messages; early return
    # if the message does not start with a '~' character
    if message.content[0] != '~':
        return

    # Set command message lowercase and split by whitespace
    cmd = message.content.lower().split()

#TODO:  better command sanitization?
#       invalid input checking?

    if cmd[0] == '~.watch_channel':
        # Set bot to watch a certain channel for the guild
        # - cmd[1] should be the channel ID as a string

        # Quietly exit if not enough arguments
        if len(cmd) < 2:
            return

        # Run query to update channel ID stored in guilds table for requesting guild
        DataConnector.run_query(("""UPDATE {0}.guilds
                                    SET channel_id = '{1}'
                                    WHERE guild_id = '{2}'
                                 """).format(SCHEMA_NAME, cmd[1], guild_id))
        await message.channel.send('Watching channel: ' + cmd[1])

    elif cmd[0] == '~.watch_message':
        # Set bot to watch a certain message for the guild
        # Any entries in the days table with a matching guild ID is removed
        # Add dummy entry to days table for print_info
        # - cmd[1] should be the message ID as a string

        # Quietly exit if not enough arguments
        if len(cmd) < 2:
            return

        # Run query to:
        # 1. Updates the message ID stored in guilds table for requesting guild
        # 2. Deletes any stored entries in days table for the requesting guild
        # 3. Inserts dummy entry into days table for requesting guild (for print_info)
        DataConnector.run_query(("""UPDATE {0}.guilds
                                    SET message_id = '{1}'
                                    WHERE guild_id = '{2}';
                                    DELETE FROM {0}.days
                                    WHERE guild_id = '{2}';
                                    INSERT INTO {0}.days
                                    VALUES ('{2}', '', '', '')
                                 """).format(SCHEMA_NAME, cmd[1], guild_id))
        str_final = 'Watching message: https://discord.com/channels/{}/{}/{}'
        await message.channel.send(str_final.format(guild_id, str(message.channel.id), cmd[1]))

#     elif '~.update_ut' in message.content.lower():
#         lst_members = client.get_guild(guild_id).members
#
#         df_ut = pd.DataFrame()
#         for member in lst_members:
#             name =  member.nick
#             if name is None:
#                 name = member.name
#
#             dict_data = {'user_id': str(member.id), 'nick':str(name).lower()}
#             df_data = pd.DataFrame([dict_data])
#             df_ut = pd.concat([df_ut,df_data])
#         df_ut['guild_id'] = str(guild_id)
#
#         cols = ['guild_id','user_id','nick']
#         df_ut = df_ut[cols]
#         DataConnector.run_query("DELETE FROM hasibot_dev.user_table WHERE guild_id = '" + str(guild_id) + "'")
#         DataConnector.write_data(df_ut,'hasibot_dev','user_table','append')
#         await message.channel.send('User Table Updated!')

    elif cmd[0] == '~.hasi':
        # Print out the specific day or all days
        # - cmd[1] optional day
        # Run query to get the user_id + day from the days table for the requesting guild
        df = DataConnector.read_data(("""SELECT day, user_id
                                         FROM {0}.days
                                         WHERE guild_id = '{1}'
                                      """).format(SCHEMA_NAME, guild_id))

        # Print the specific day if exists or all days
        if len(cmd) == 2 and cmd[1] in day_emotes:
            str_final = ("```md\n"    + \
                         "#{0}:\n{1}\n" + \
                         "```").format(cmd[1].capitalize(),
                                       day_print(guild_id, grab_day(df, cmd[1])))
        else:
            str_final = ("```md\n"     + \
                         "#Sun:\n{0}\n" + \
                         "#Mon:\n{1}\n" + \
                         "#Tue:\n{2}\n" + \
                         "#Wed:\n{3}\n" + \
                         "#Thu:\n{4}\n" + \
                         "#Fri:\n{5}\n" + \
                         "#Sat:\n{6}\n" + \
                         "```").format(day_print(guild_id, grab_day(df, 'sun')),
                                       day_print(guild_id, grab_day(df, 'mon')),
                                       day_print(guild_id, grab_day(df, 'tue')),
                                       day_print(guild_id, grab_day(df, 'wed')),
                                       day_print(guild_id, grab_day(df, 'thu')),
                                       day_print(guild_id, grab_day(df, 'fri')),
                                       day_print(guild_id, grab_day(df, 'sat')))
        await message.channel.send(str_final)

    elif cmd[0] == '~.roll_echo':
        # Roll a g30 echostone at normal rates (adv Sidhe)
        attempts, total_stat = get_echo_30()

        resp = "It took {} attempts! The total stat is: {}".format(attempts, total_stat)

        await message.channel.send(resp)

    elif cmd[0] == '~.roll_boosted_echo':
        # Roll a g30 echostone at event rates (adv Sidhe + 10%)
        attempts, total_stat = get_boosted_echo_30()

        resp = "It took {} attempts! The total stat is: {}".format(attempts, total_stat)

        await message.channel.send(resp)

    elif cmd[0] == '~.print_info':
        # Prints some metadata and day counts
        # - cmd[1] optional gid flag
        # - cmd[2] if gid flag supplied, this is the guild ID as a string
        query = open('data/day_query.txt').read().format(SCHEMA_NAME)
        df = DataConnector.read_data(query)

        # Add guild names for all found guilds
        dict_map = {}
        for i in client.guilds:
            dict_map[str(i.id)] = i.name

        # Add in guild name to the DataFrame
        df['guild_name'] = df['guild_id'].map(dict_map)
        cols = ['guild_name','guild_id','channel_id','message_id','sun','mon','tue','wed','thu','fri','sat']
        df = df[cols]

        # Print out a specific guild if the command length and flag are correct
        if len(cmd) == 3 and cmd[1] == 'gid':
            df = df[df['guild_id'] == cmd[2]]

        str_final = "```\n" + str(df.transpose()) + "\n```"
        await message.channel.send(str_final)

    elif cmd[0] == '~.search':
        # Run Jerry search
        # - cmd[1]    type of search
        #   > item, items
        #   > es
        # - cmd[2...] name of what to search

        # Quietly exit if not enough arguments
        if len(cmd) < 3:
            return

        # Combine the search term to a string
        term = ""
        for word in cmd[2:]:
            term = term + word + " "
        # Remove extra space
        term = term[:-1]

        if cmd[1] == 'item' or cmd[1] == 'items':
            # Search for an item
            the_link2 = "https://wiki.mabinogiworld.com/index.php?search=" + term.replace(" ", "%20")

            main_url = 'https://api.mabibase.com/items/search/name/{}'.format(term)
            response = requests.get(url = main_url)

            if response.json()['data']['items'] == []:
                await message.channel.send(content='No result\n' + the_link2)
                return

            item_id = response.json()['data']['items'][0]['id']

            the_link = "https://mabibase.com/item/" + str(item_id)
            final_link = the_link + "\n" + the_link2

            url = 'https://api.mabibase.com/item/{}'.format(item_id)
            response2 = requests.get(url = url)

            df = pd.DataFrame([response2.json()['data']['item']])

            df_final = df[df.columns.intersection(lst_scols)]

            try:
                xml_string = df_final['xml_string'][0]
                etree = ET.fromstring(xml_string)
                for item in etree.items():
                    df_final[item[0]] = item[1]
            except Exception as ex:
                print(ex)

            try:
                lst_effects = df_final['set_effects'][0]['effects']
                for item in lst_effects:
                    df_final[item['name']] = item['value']
            except Exception as ex:
                print(ex)

            try:
                lst_rolls = df_final['random_product'][0].split(";")
                for str_ in lst_rolls:
                    pos_comma = str_.find(",")
                    df_final[str_[:pos_comma]] = str_[pos_comma+1:]

            except Exception as ex:
                print(ex)

            df_final = df_final.drop(columns=['xml_string','set_effects','random_product'], axis=1, errors='ignore')

            obj_embed = discord.Embed(title=df['name'][0], description=df['description'][0])
            url = "https://api.mabibase.com/icon/item/" + str(item_id)
            obj_embed.set_image(url=url)

            str_final = "```\n" + str(df_final.transpose()) + "\n```"

            await message.channel.send(embed=obj_embed, content=final_link)
            await message.channel.send(content=str_final)

        elif cmd[1] == 'es':
            # Search for an enchant scroll
            main_url = 'https://api.mabibase.com/enchants/search?q=name,{}'.format(term)
            response = requests.get(url = main_url)

            df = pd.DataFrame([response.json()['data']['enchants'][0]])

            try:
                lst_modifiers = df['modifiers'][0]

                for mod in lst_modifiers:
                    df[mod['effect']['arguments'][0]] = mod['effect']['arguments'][1]
            except Exception as ex:
                print(ex)

            df_final = df

            df_final = df_final.drop(columns=['modifiers'], axis=1, errors='ignore')
            str_final = "```\n" + str(df_final.transpose()) + "\n```"

            link = "https://mabibase.com/enchants/search?q=name," + term

            await message.channel.send(content=link)
            await message.channel.send(content=str_final)

# Run the bot
client.run(TOKEN)