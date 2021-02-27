# Standard Library
import datetime

# Third Party Library
import pandas as pd
import requests
import discord
import xml.etree.ElementTree as ET

# Application Specific Library
from config import SCHEMA_NAME, lst_scols, DB_URL, time_zone, PATH
from .momento import get_echo_30, get_boosted_echo_30
from .helpers import grab_day, day_print
from .connector import DataConnector


class DataProcessor():
    day_emotes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

    @classmethod
    def _on_ready(cls, guilds):
        '''
        Executes when the Discord bot first starts.
        - Retrieves a list of guilds currently in the DB
        - Checks if any guilds this bot currently is active in are not in the DB
        - If non-existent, creates an entry in the DB for the guild
        '''
        # Create the DB connection on start up
        DataConnector.create_engine(DB_URL)
        guild_list_changed = False

        # Request the current list of guilds; create a DataFrame in case the
        # database is empty
        df_all_guilds = pd.DataFrame()
        df = DataConnector.read_data('SELECT * FROM {}.guilds'.format(SCHEMA_NAME))
        df_all_guilds = pd.concat([df_all_guilds,df])
        lst_db_guilds = df_all_guilds['guild_id'].tolist()

        # Compare the guilds the bot is currently in versus what is stored in
        # the database
        for guild in guilds:
            guild_id = str(guild.id)
            if guild_id not in lst_db_guilds:
                # If a guild does not exist in the database, create a new row
                dict_guild = {'guild_id': guild_id, 'channel_id': '','message_id': ''}
                df_guild = pd.DataFrame([dict_guild])
                df_all_guilds = pd.concat([df_all_guilds,df_guild])
                guild_list_changed = True
            else:
                # Else, remove that guild from the guild list
                lst_db_guilds.remove(guild_id)

        # If the list of guilds in the database is not 0, then the bot was
        # removed from a guild while the bot was offline
        if len(lst_db_guilds) != 0:
            guild_list_changed = True
            for guild in lst_db_guilds:
                # Remove the guild from the df
                df_all_guilds = df_all_guilds[df_all_guilds != guild]
            # Current implentation inserst NaN values into the df in place of
            # the deleted rows
            df_all_guilds.dropna(inplace=True)

        # Update the database if a new guild was added or if a guild was removed
        # while the bot was offline
        if guild_list_changed == True:
            # Truncate the table and insert the new guild list
            DataConnector.run_query("TRUNCATE TABLE {}.guilds".format(SCHEMA_NAME))
            DataConnector.write_data(df_all_guilds, SCHEMA_NAME, 'guilds', 'append')

        print("Bot is ready!")

    @classmethod
    def _on_guild_join(cls, guild):
        '''
        Executes when the Discord bot joins a guild.
        - Inserts the supplied guild ID into the guilds table
        - Inserts a dummy value into the days table for print_info
    
        Arguments:
        - guild   int   the guild ID
        '''
        # This query checks if an entry already exists before inserting into the table.
        # If the entry exists, nothing is done.
        query = open(PATH + "data/guild_join_query.txt").read().format(SCHEMA_NAME, str(guild.id))
        DataConnector.run_query(query)

    @classmethod
    def _on_guild_remove(cls, guild):
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

    @classmethod
    def _on_raw_reaction_add(cls, client, payload):
        '''
        Executes when a reaction in a guild is added.
        - Returns if the guild's watched channel and message have not been set
        - Returns if the payload's message id is not the one being watched
        - On new reacts to the watched message, add the user ID that reacted to a
          queue for the reacted day

        Arguments:
        - client    Client                  a Discord class
        - payload   RawReactionActionEvent  a Discord object
        '''
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
            if day in cls.day_emotes:
                now = datetime.datetime.now(time_zone).strftime("%Y-%m-%d_%H:%M:%S.%f")
                dict_val = {'guild_id':guild_id, 'day':str(day), 'user_id':str(payload.member.id), 'insert_ts':now}
                df_val = pd.DataFrame([dict_val])
                DataConnector.write_data(df_val, SCHEMA_NAME, 'days')
        
    @classmethod
    def _on_raw_reaction_remove(cls, client, payload):
        '''
        Executes when a reaction in a guild is removed.
        - Returns if the guild's watched channel and message have not been set
        - Returns if the payload's message id is not the one being watched
        - On unreacts to the watched message, remove the user ID that unreacted from
          the queue for the unreacted day
    
        Arguments:
        - client    Client                  a Discord class
        - payload   RawReactionActionEvent  a Discord class
        '''
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
                                              day = '{2}' AND
                                              guild_id = '{3}'
                                     """).format(SCHEMA_NAME, user, day, guild_id))

    @classmethod
    def _on_message_watch_channel(cls, guild_id, channel_id):

        # Set bot to watch a certain channel for the guild
        # - cmd[1] should be the channel ID as a string

        # Run query to update channel ID stored in guilds table for requesting guild
        DataConnector.run_query(("""UPDATE {0}.guilds
                                    SET channel_id = '{1}'
                                    WHERE guild_id = '{2}'
                                 """).format(SCHEMA_NAME, channel_id, guild_id))

    @classmethod
    def _on_message_watch_message(cls, guild_id, message_id):
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
                                 """).format(SCHEMA_NAME, message_id, guild_id))
        df = DataConnector.read_data(("""SELECT channel_id,message_id 
                                    FROM {}.guilds 
                                    WHERE guild_id = '{}'
                                 """).format(SCHEMA_NAME,guild_id))
        cid = df['channel_id'][0]
        mid = df['message_id'][0]
        str_final = 'Watching message: https://discord.com/channels/{}/{}/{}'.format(guild_id,cid,mid)

        return str_final

    @classmethod
    def _on_message_hasi(cls, client, guild_id, day):

        # Print out the specific day or all days
        # - cmd[1] optional day
        # Run query to get the user_id + day from the days table for the
        # requesting guild, ordered by the timestamp (ascending)
        df = DataConnector.read_data(("""SELECT day, user_id
                                         FROM {0}.days
                                         WHERE guild_id = '{1}'
                                         ORDER BY insert_ts ASC
                                      """).format(SCHEMA_NAME, guild_id))

        # Print the specific day if exists or all days
        if day in cls.day_emotes:
            str_final = ("```md\n"    + \
                         "#{0}:\n{1}\n" + \
                         "```").format(day.capitalize(),
                                       day_print(client, guild_id, grab_day(df, day)))
        else:
            str_final = ("```md\n"     + \
                         "#Sun:\n{0}\n" + \
                         "#Mon:\n{1}\n" + \
                         "#Tue:\n{2}\n" + \
                         "#Wed:\n{3}\n" + \
                         "#Thu:\n{4}\n" + \
                         "#Fri:\n{5}\n" + \
                         "#Sat:\n{6}\n" + \
                         "```").format(day_print(client, guild_id, grab_day(df, 'sun')),
                                       day_print(client, guild_id, grab_day(df, 'mon')),
                                       day_print(client, guild_id, grab_day(df, 'tue')),
                                       day_print(client, guild_id, grab_day(df, 'wed')),
                                       day_print(client, guild_id, grab_day(df, 'thu')),
                                       day_print(client, guild_id, grab_day(df, 'fri')),
                                       day_print(client, guild_id, grab_day(df, 'sat')))

        return str_final


    @classmethod
    def _on_message_print_info(cls, client, guild_id=''):
        # Prints some metadata and day counts
        # - cmd[1] optional gid flag
        # - cmd[2] if gid flag supplied, this is the guild ID as a string
        query = open(PATH + 'data/day_query.txt').read().format(SCHEMA_NAME)
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
        if guild_id != '':
            df = df[df['guild_id'] == guild_id]

        str_final = "```\n" + str(df.transpose()) + "\n```"

        return str_final

    @classmethod
    def _erg(cls, guild_id, user_id):
        df = DataConnector.read_data("SELECT * FROM {}.erg WHERE user_id='{}'".format(SCHEMA_NAME,user_id)) 
        if df.shape[0] == 0:
            success = roll_erg(0)
            if success:
                DataConnector.run_query("INSERT INTO {}.erg VALUES ({},1,1,0,1)".format(SCHEMA_NAME,user_id))
            else:
                DataConnector.run_query("INSERT INTO {}.erg VALUES ({},0,1,0,1)".format(SCHEMA_NAME,user_id))
        else:
            success = roll_erg(df['erg_rank'][0])
            if success:
                if df['erg_rank'][0] < 8:
                    query = "UPDATE {}.erg SET erg_rank = erg_rank + 1,current_count = 0, total_count = total_count + 1 WHERE user_id={}".format(SCHEMA_NAME,user_id)
                           
        

    @classmethod
    def _on_message_roll_echo(cls):

        # Roll a g30 echostone at normal rates (adv Sidhe)
        attempts, total_stat = get_echo_30()

        str_final = "It took {} attempts! The total stat is: {}".format(attempts, total_stat)

        return str_final

    @classmethod
    def _on_message_roll_boosted_echo(cls):

        # Roll a g30 echostone at event rates (adv Sidhe + 10%)
        attempts, total_stat = get_boosted_echo_30()

        str_final = "It took {} attempts! The total stat is: {}".format(attempts, total_stat)

        return str_final

    @classmethod
    def _on_message_search(cls, option, term):
        # Run Jerry search
        # - cmd[1]    type of search
        #   > item, items
        #   > es
        # - cmd[2...] name of what to search
        dict_res = {}

        if option == 'item' or option == 'items':
            # Search for an item
            the_link2 = "https://wiki.mabinogiworld.com/index.php?search=" + term.replace(" ", "%20")

            main_url = 'https://api.mabibase.com/items/search/name/{}'.format(term)
            response = requests.get(url = main_url)

            if response.json()['data']['items'] == []:
                dict_res['status'] = 0
                dict_res['str_final'] = "No result\n{}".format(the_link2)
                return dict_res

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

            dict_res['status'] = 1
            dict_res['str_final'] = "```\n" + str(df_final.transpose()) + "\n```"
            dict_res['obj_embed'] = obj_embed
            dict_res['final_link'] = final_link

            return dict_res
        elif option == 'es':
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

            dict_res['status'] = 2
            dict_res['link'] = link
            dict_res['str_final'] = str_final

            return dict_res
        else:
            dict_res['status'] = -1

            return dict_res
