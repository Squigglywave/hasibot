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

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

USER=os.getenv('USER')
DATABASE=os.getenv('DATABASE')
HOST=os.getenv('HOST')
PORT=os.getenv('PORT')
PASSWORD=os.getenv('PASSWORD')

intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)

###########
# Globals #
###########
# List of acceptable day emoji names, should match what is stored in guilds var
day_emotes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

def day_print(guild_id, lst_users):
    ret_str = ""

    for n,user_id in enumerate(lst_users):
        user = client.get_guild(int(guild_id)).get_member(int(user_id)) 
        if user.nick is not None:
            name = user.nick
        else:
            name = user.name
        ret_str = ret_str + "    " + str(n+1) + ". " + name + "\n"

    return ret_str

def grab_day(df,day):
    try:
        lst_day = df.groupby('day')['user_id'].unique()[day]
    except Exception as ex:
        lst_day = []
    return lst_day

@client.event
async def on_ready():
    DataConnector.create_engine(USER, PASSWORD, HOST, PORT, DATABASE)
    df_all_guilds = pd.DataFrame()
    df = DataConnector.read_data('SELECT * FROM hasibot_dev.guilds')
    df_all_guilds = pd.concat([df_all_guilds,df])
    async for guild in client.fetch_guilds(limit=150):
        if str(guild.id) not in df_all_guilds['guild_id'].tolist():
            dict_guild = {'guild_id':str(guild.id), 'channel_id':'','message_id':''}
            df_guild = pd.DataFrame([dict_guild])
            df_all_guilds = pd.concat([df_all_guilds,df_guild])
    
    DataConnector.run_query("TRUNCATE TABLE hasibot_dev.guilds")
    DataConnector.write_data(df_all_guilds, 'hasibot_dev','guilds', 'append')
    print("Bot is ready!")

@client.event
async def on_guild_join(guild):
    query = open("data/guild_join_query.txt").read().replace("\n"," ").format(str(guild.id))
    DataConnector.run_query(query)

@client.event
async def on_guild_remove(guild):
    DataConnector.run_query("DELETE FROM hasibot_dev.guilds WHERE guild_id = '" + str(guild.id) + "';" + \
                            "DELETE FROM hasibot_dev.days WHERE guild_id = '" + str(guild.id) + "';")

@client.event
async def on_raw_reaction_add(payload):
    global day_emotes
    guild_id = str(payload.guild_id)
    df_channel = DataConnector.read_data("SELECT message_id,channel_id FROM hasibot_dev.guilds WHERE guild_id = '" + guild_id + "'")
    channel = client.get_channel(int(df_channel['channel_id'][0]))

    message_id = df_channel['message_id'][0]
    if (channel is None) or (message_id == ''):
        return
    
    if payload.message_id == int(message_id):
        day = payload.emoji.name
        if day in day_emotes:
            now = datetime.datetime.now(time_zone).strftime("%Y-%m-%d_%H:%M:%S.%f")
            dict_val = {'guild_id':guild_id,'day':str(day),'user_id':str(payload.member.id), 'insert_ts':now}
            df_val = pd.DataFrame([dict_val])
            DataConnector.write_data(df_val, 'hasibot_dev','days')

@client.event
async def on_raw_reaction_remove(payload):
    global day_emotes
    guild_id = str(payload.guild_id)
    df_channel = DataConnector.read_data("SELECT message_id,channel_id FROM hasibot_dev.guilds WHERE guild_id = '" + guild_id + "'")
    channel = client.get_channel(int(df_channel['channel_id'][0]))
 
    message_id = df_channel['message_id'][0]
    if (channel is None) or (message_id == ''):
        return

    if payload.message_id == int(message_id):
        user = str(payload.user_id)
        day = str(payload.emoji.name)
        DataConnector.run_query("DELETE FROM hasibot_dev.days WHERE user_id='" + user + "' AND day = '" + day + "'")

@client.event
async def on_message(message):
    global day_emotes
    guild_id = str(message.guild.id)

    if '~.watch_channel' in message.content.lower():
        str_input = message.content.lower()
        DataConnector.run_query("UPDATE hasibot_dev.guilds SET channel_id = '" + \
                                 str_input[16:] + "' WHERE guild_id='" + str(guild_id) + "'")

        await message.channel.send('Watching channel: ' + str_input[16:])
    elif '~.watch_message' in message.content.lower():         
        str_input = message.content.lower()
        DataConnector.run_query("UPDATE hasibot_dev.guilds SET message_id = '" + \
                                 str_input[16:] + "' WHERE guild_id='" + guild_id + "';" + \
                                 "DELETE FROM hasibot_dev.days WHERE guild_id='" + guild_id + "';"+ \
                                 "INSERT INTO hasibot_dev.days VALUES ('" + guild_id + "', '', '', '')")
        await message.channel.send('Watching message: ' + str_input[16:])
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
    elif '~.hasi' in message.content.lower():
        str_input = message.content.lower()[7:]
        df = DataConnector.read_data("SELECT * FROM hasibot_dev.days WHERE guild_id = '" + guild_id + "'")
        
        if str_input in day_emotes:
            str_final = "```md\n#" + str_input.capitalize() + ":\n{}\n```".format(day_print(guild_id,grab_day(df,str_input)))
        else:
            str_final = "```md\n#Sun:\n{}\n#Mon:\n{}\n#Tue:\n{}\n#Wed:\n{}\n#Thu:\n{}\n#Fri:\n{}\n#Sat:\n{}\n```".format(
                                                               day_print(guild_id,grab_day(df,'sun')),
                                                               day_print(guild_id,grab_day(df,'mon')),
                                                               day_print(guild_id,grab_day(df,'tue')),
                                                               day_print(guild_id,grab_day(df,'wed')),
                                                               day_print(guild_id,grab_day(df,'thu')),
                                                               day_print(guild_id,grab_day(df,'fri')),
                                                               day_print(guild_id,grab_day(df,'sat')))
        await message.channel.send(str_final)
    elif '~.roll_echo' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[12:]
        attempts,total_stat = get_echo_30()
        
        resp = "It took {} attempts! The total stat is: {}".format(attempts,total_stat)
        
        await message.channel.send(str(resp))
    elif '~.roll_boosted_echo' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[19:]
        attempts,total_stat = get_boosted_echo_30()

        resp = "It took {} attempts! The total stat is: {}".format(attempts,total_stat)
        
        await message.channel.send(str(resp))
    elif '~.print_info' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[13:]
        lst_args = str_input.split(" ")

        query = open('data/day_query.txt').read().replace('\n',' ')
        df = DataConnector.read_data(query)
        dict_map = {}
        for i in client.guilds:
            dict_map[str(i.id)] = i.name

        df['guild_name'] = df['guild_id'].map(dict_map) 
        cols = ['guild_name','guild_id','channel_id','message_id','sun','mon','tue','wed','thu','fri','sat']
        df = df[cols]

        if lst_args[0].lower() == 'gid' and len(lst_args) == 2:
            df = df[df['guild_id'] == lst_args[1]]

        str_final = "```\n" + str(df.transpose()) + "\n```"
        await message.channel.send(str_final)
    elif '~.search items' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[15:]

        the_link2 = "https://wiki.mabinogiworld.com/index.php?search=" + str_input

        main_url = 'https://api.mabibase.com/items/search/name/{}'.format(str_input)
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
    elif '~.search es' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[12:]
        
        main_url = 'https://api.mabibase.com/enchants/search?q=name,{}'.format(str_input)
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
        
        link = "https://mabibase.com/enchants/search?q=name," + str_input
        
        await message.channel.send(content=link)
        await message.channel.send(content=str_final)
client.run(TOKEN)
