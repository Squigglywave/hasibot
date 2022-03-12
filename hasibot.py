# Standard Library
import io
import datetime
import random

# Third Party Library
import requests
import discord
import pandas as pd
import aiocron

# Application Specific Library
from utils import DataProcessor
from config import TOKEN, PATH, erg_rates

# Intents used to track guild member lists
intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)

###########
# Globals #
###########
# List of acceptable day emoji names; Discord server needs to name the emojis in
# this exact format
day_emotes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'yes']

###################
# Discord Methods #
###################
@client.event
async def on_ready():
    '''
    Initial discord call when launching bot.
    '''
    DataProcessor._on_ready(client.guilds)

@client.event
async def on_guild_join(guild):
    '''
    Discord call when bot joins a new guild.
    '''
    DataProcessor._on_guild_join(guild)

@client.event
async def on_guild_remove(guild):
    '''
    Discord call when bot leaves a guild.
    '''
    DataProcessor._on_guild_remove(guild)

@client.event
async def on_raw_reaction_add(payload):
    '''
    Discord call when a person reacts to a message.
    '''
    DataProcessor._on_raw_reaction_add(client, payload)

@client.event
async def on_raw_reaction_remove(payload):
    '''
    Discord call when a person unreacts to a message.
    '''
    DataProcessor._on_raw_reaction_remove(client, payload)

@client.event
async def on_message(message):
    '''
    Parses through all messages in the discord server.
    - Early exit if the message does not start with the correct prefix
    - Watches for the following commands (not case sensitive):
      > watch_channel
      > watch_message
      > hasi
      > print_info
      > erg
      > roll_echo
      > roll_boosted_echo
      > search items
      > search es

    Arguments:
    - message   Message   a Discord object
    '''
    global day_emotes
    guild_id = str(message.guild.id)
    user_message_id = str(message.author.id)

    # Quick optimization as this bot is watching all messages; early return
    # if the message does not start with a '~' character
    try:
        if message.content[0] != '~':
            return
    except:
        return

    # Set command message lowercase and split by whitespace
    cmd = message.content.lower().split()

    # Check input
    if cmd[0] == '~.help':
        if len(cmd) > 1:
            desired_info = cmd[1]
            # make logic to give help for each command here...
            
        str_final = """
```
~.watch_channel <CHANNEL_ID>
  Used to select which channel to watch. Must be set to something.

~.watch_message <MESSAGE_ID>
  Used to select which message to watch. Must be set to something.

~.setbirthday <MM/DD>
  Used to set a birthday for a person. Hasibot will automatically send a birthday message on that day!

~.hasi <day>
  Displays the queue for the requested day. Accepted values:
    sun
    mon
    tue
    wed
    thu
    fri
    sat
    default (no argument) - displays all days
  
~.print_info <gid> #
  Prints guild IDs, channel IDs, message IDs, and body counts for all guilds.
  If the gid flag is supplied, then only prints the above information for that specific guild.

~.roll_echo
  Rolls a g30 echostone with adv rates. Prints number of attempts and final echostone stat.
  
~.roll_boosted_echo
  Rolls a g30 echostone with adv rates + 10% bonus. Prints number of attempts and final echostone stat.
```
        """
        await message.channel.send(str_final)
    elif cmd[0] == '~.watch_channel':
        # Check for channel ID, return if no second argument
        if len(cmd) < 2:
            return
        DataProcessor._on_message_watch_channel(guild_id, cmd[1])
        await message.channel.send('Watching channel: ' + cmd[1])
    elif cmd[0] == '~.watch_message':
        # Set bot to watch a certain message for the guild
        # Any entries in the days table with a matching guild ID is removed
        # Add dummy entry to days table for print_info
        # - cmd[1] should be the message ID as a string

        # Quietly exit if not enough arguments
        if len(cmd) < 2:
            return

        str_final = DataProcessor._on_message_watch_message(guild_id, cmd[1])

        await message.channel.send(str_final)
    elif cmd[0] == '~.hasi':
        day = ''
        if len(cmd) > 1:
            day = cmd[1]
            
        str_final = DataProcessor._on_message_hasi(client, guild_id, day)
        await message.channel.send(str_final)
    elif cmd[0] == '~.print_info':
        gid = ''
        if len(cmd) == 3 and cmd[1] == 'gid':
             gid = cmd[2]

        str_final = DataProcessor._on_message_print_info(client, gid)
        await message.channel.send(str_final)
    elif cmd[0] == '~.set_bday':
        if len(cmd) > 1:
            if len(cmd) > 2:
                str_final = DataProcessor._set_birthday(client, guild_id, cmd[1], cmd[2])
            else:
                str_final = "Not enough elements passed, please pass in month and day in this format: Name MM/DD"
        else:
            str_final = "No element passed, please pass in month and day in this format: Name MM/DD"
        await message.channel.send(str_final)
    elif cmd[0] == '~.unset_bday':
        if len(cmd) > 1:
            str_final = DataProcessor._unset_birthday(client, guild_id, cmd[1])
        else:
            str_final = "Please provide name of person to unset"
            
        await message.channel.send(str_final)
    elif cmd[0] == '~.print_bdays':
        str_final = DataProcessor._print_bdays(client, guild_id)

        await message.channel.send(str_final)
    elif cmd[0] == '~.set_bday_channel':
        if len(cmd) > 1:
            channel_id = str(cmd[1])
            str_final = DataProcessor._set_bday_channel(client, guild_id, channel_id)
        else:
            str_final = "Please provide channel ID for bot to send messages"
            
        await message.channel.send(str_final)
    
    elif cmd[0] == '~.erg':
        df_erg,success = DataProcessor._erg(user_message_id)
        if df_erg.shape[0] == 0:
            dict_erg = {
                        'total_erg_weps':0,
                        'erg_rank':0,
                        'current_count':0,
                        'total_count':0
                       }
            df_erg = pd.DataFrame([dict_erg])
        current_rank = df_erg['erg_rank'][0]
        df_erg['erg_rank'] = df_erg['erg_rank'] *5+5
        if success:
            df_erg['erg_rank'] = df_erg['erg_rank'] + 5
            df_erg['current_count'] = df_erg['current_count'] + 1
            #str_final = "```\nSuccess Rate: {}%\n# of Weapons: {}\nErg Rank: {}\n# of Attempts: {}\nTotal Attempts: {}\n```".format(int(erg_rates[current_rank]*100),df_erg['total_erg_weps'][0],df_erg['erg_rank'][0],df_erg['current_count'][0],df_erg['total_count'][0])
            str_final = ("```\nSuccess Rate: {:.2f}%\n" + \
                         "# of Weapons: {}\n"    + \
                         "Erg Rank: {}\n"        + \
                         "# of Attempts: {}\n"   + \
                         "Total Attempts: {}\n```").format(erg_rates[current_rank]*100,
                                                        df_erg['total_erg_weps'][0],
                                                        df_erg['erg_rank'][0],
                                                        df_erg['current_count'][0],
                                                        df_erg['total_count'][0])
            #str_final = "```\n" + str(df_erg.transpose()) + "\n```"
            embed = discord.Embed(title=message.author.name, description=str_final, color=0x00ff00)
            file_1 = discord.File(PATH + "data/ergsuccess.png", filename="image.png")
            embed.set_image(url="attachment://image.png")
            await message.channel.send(embed=embed, file=file_1)
        else:
            df_erg['current_count'] = df_erg['current_count'] + 1
            #str_final = "```\nSuccess Rate: {}%\n# of Weapons: {}\nErg Rank: {}\n# of Attempts: {}\nTotal Attempts: {}\n```".format(int(erg_rates[current_rank]*100),df_erg['total_erg_weps'][0],df_erg['erg_rank'][0],df_erg['current_count'][0],df_erg['total_count'][0])
            str_final = ("```\nSuccess Rate: {:.2f}%\n" + \
                         "# of Weapons: {}\n"    + \
                         "Erg Rank: {}\n"        + \
                         "# of Attempts: {}\n"   + \
                         "Total Attempts: {}\n```").format(erg_rates[current_rank]*100,
                                                        df_erg['total_erg_weps'][0],
                                                        df_erg['erg_rank'][0],
                                                        df_erg['current_count'][0],
                                                        df_erg['total_count'][0])
            embed = discord.Embed(title=message.author.name, description=str_final, color=0xcb4154)
            roll = random.random()
            if roll < 0.10:
                file_1 = discord.File(PATH + "data/hahafrog.png", filename="image.png")
            else:
                file_1 = discord.File(PATH + "data/ergfail.png", filename="image.png")
            embed.set_image(url="attachment://image.png")
            await message.channel.send(embed=embed, file=file_1)
    elif cmd[0] == '~.roll_echo':
        str_final = DataProcessor._on_message_roll_echo()

        await message.channel.send(str_final)
    elif cmd[0] == '~.roll_boosted_echo':
        str_final = DataProcessor._on_message_roll_boosted_echo()

        await message.channel.send(str_final)
    elif cmd[0] == '~.search':
        str_usage = "```\nUsage: ~.search <options> <name>\noptions:\n    item, items,\n    es\n```"
        # Quietly exit if not enough arguments
        if len(cmd) < 3:
            await message.channel.send(content=str_usage)
            return

        # Combine the search term to a string
        term = ""
        for word in cmd[2:]:
            term = term + word + " "
        # Remove extra space
        term = term[:-1]

        dict_res = DataProcessor._on_message_search(cmd[1], term)

        if dict_res['status'] == -1:
            await message.channel.send(content=str_usage)
        elif dict_res['status'] == 0:
            await message.channel.send(content=dict_res['str_final'])
        elif dict_res['status'] == 1:
            await message.channel.send(embed=dict_res['obj_embed'], content=dict_res['final_link'])
            await message.channel.send(content=dict_res['str_final'])
        elif dict_res['status'] == 2:
            await message.channel.send(content=dict_res['link'])
            await message.channel.send(content=dict_res['str_final'])
    elif cmd[0] == '~.sendbday':
        await DataProcessor._send_bday(client)


# Scheduled task for birthdays!
@aiocron.crontab('0 0 * * *')
async def cronjob1():
    await DataProcessor._send_bday(client)

# Run the bot
client.run(TOKEN)
