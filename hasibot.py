# Standard Library
import io
import datetime
import random
import urllib.request
import re
import time

# Third Party Library
import requests
import discord
from discord.utils import get
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
latest_yt_url = ""

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
    global latest_yt_url
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
    original_cmd = message.content.split()
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

~.set_bday_channel <CHANNEL_ID>
  Used to select a channel for hasibot to give birthday announcements. A channel must be set for hasibot to start monitoring birthdays.

~.set_bday <MM/DD>
  Used to set a birthday for a person. Hasibot will automatically send a birthday message on that day.

~.unset_bday <name>
  Used to unset a birthday. Hasibot will no longer send a birthday after this command.

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
                username = " ".join(cmd[1:-1])
                str_final = DataProcessor._set_birthday(client, guild_id, username, cmd[-1])
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
    elif cmd[0] == '~.time':
        await message.channel.send(str(datetime.datetime.now()))
    elif cmd[0] == '~.set_meko_channel':
        if len(cmd) > 1:
            channel_id = str(cmd[1])
            str_final = DataProcessor._set_db_channel('meko_channels',client, guild_id, channel_id)
        else:
            str_final = "Please provide channel ID for bot to send messages"
            
        await message.channel.send(str_final)
    elif cmd[0] == "~.farmmeko":
        await DataProcessor._farm_mekos(client, guild_id, user_message_id)
    elif cmd[0] == "~.eval":
        if len(cmd) < 2:
            str_usage = "Please provide an expression like 1+1"
            await message.channel.send(content=str_usage)
        else:
            try:
                result = str(eval(cmd[1]))
            except Exception as ex:
                result = "Expression could not be evaluated, please enter proper expression"
            await message.channel.send(content=result)
    elif cmd[0] == "~.join":
        if len(cmd) < 2:
            str_usage = "Please provide a voice channel id"
            await message.channel.send(content=str_usage)
        
        channel_id = cmd[1]
        voice_channel = client.get_channel(int(channel_id))
        
        await voice_channel.connect()
        #import time
        #time.sleep(3)
        #guild = message.guild.voice_client
        #await guild.disconnect()
        
        print("END")
    elif cmd[0] == "~.leave":
        #if len(cmd) < 2:
        #    str_usage = "Please provide guild id on which guild to leave the voice chat"
        #    await message.channel.send(content=str_usage)
        
        #guild_id = cmd[1]
        guild = client.get_guild(int(guild_id)).voice_client
        await guild.disconnect()
        
        #import pdb; pdb.set_trace();
        
        print("END")
    elif cmd[0] == "~.search":
        if len(cmd) < 2:
            str_usage = "Please provide search arguement"
            await message.channel.send(content=str_usage)
        else:

            search_keyword = "+".join(cmd[1:-1])
            html = urllib.request.urlopen("https://www.youtube.com/results?search_query=" + search_keyword)
            video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
            if len(video_ids) == 0:
                await message.channel.send(content="No result found.")
            else:
                latest_yt_url = "https://www.youtube.com/watch?v=" + video_ids[0]
                await message.channel.send(content=latest_yt_url)
    elif cmd[0] == "~.play":
        input_url = ""
        if len(cmd) > 1:
            input_url = original_cmd[1]
            
        if latest_yt_url == "" and input_url == "":
            result = DataProcessor._play_song(client,guild_id,input_url)
            await message.channel.send(content=result)
        else:
            if input_url == "":
                result = DataProcessor._play_song(client,guild_id,latest_yt_url)
                await message.channel.send(content=result)
            else:
                result = DataProcessor._play_song(client,guild_id,input_url)
                await message.channel.send(content=result)
    elif cmd[0] == "~.stop":
        guild = client.get_guild(int(guild_id))
        voice = get(client.voice_clients, guild=guild)
        
        voice.stop()
        
        await message.channel.send("Song Stopped.")
    elif cmd[0] == "~.add":
        if len(cmd) < 2:
            str_usage = "Please provide a youtube url to add"
        else:
            song_url = original_cmd[1]
            result = DataProcessor._add_song(client, guild_id, song_url)
            
            await message.channel.send(content=result)
    elif cmd[0] == "~.list":
        result = DataProcessor._list_songs(client,guild_id)
        
        await message.channel.send(content=result)

    elif cmd[0] == "~.clear":
        result = DataProcessor._clear_songs(client,guild_id)
        
        await message.channel.send(content=result)
    elif cmd[0] == "~.skip":
        guild = client.get_guild(int(guild_id))
        voice = get(client.voice_clients, guild=guild)
        
        voice.stop()
        await message.channel.send("Song skipped.")

        guild = client.get_guild(int(guild_id))
        voice = get(client.voice_clients, guild=guild)
        
        YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
        FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        
        if not voice.is_playing():
            next_song = DataProcessor._get_next_song(guild_id)
            while next_song != "":
                if voice.is_playing():
                    time.sleep(1)
                else:
                    with YoutubeDL(YDL_OPTIONS) as ydl:
                        info = ydl.extract_info(next_song, download=False)
                    URL = info['formats'][0]['url']
                    
                    voice.play(FFmpegPCMAudio(URL, **FFMPEG_OPTIONS))
                    voice.is_playing()
                    DataProcessor._delete_song(guild_id,next_song)
                    next_song = DataProcessor._get_next_song(guild_id)
        else:
            await message.channel.send("Already playing song")
        
        
        


# Scheduled task for birthdays!
@aiocron.crontab('0 0 * * *')
async def cronjob1():
    await DataProcessor._send_bday(client)

@aiocron.crontab('0 0 * * *')
async def cronjob1():
    await DataProcessor._farm_mekos(client)

# Run the bot
client.run(TOKEN)
