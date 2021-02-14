# Standard Library
import os
import io
import xml.etree.ElementTree as ET

# Third Party Library
import requests
import discord
from dotenv import load_dotenv
import pandas as pd

# Application Specific Library
from utils import get_echo_30
from config import lst_scols

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()

###########
# Globals #
###########
# List of acceptable day emoji names, should match what is stored in guilds var
day_emotes = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
guilds = {}

# Dumps all data stored in the given 'guilds' entry
def init_guilds(arg, channel_id):
    global guilds

    guilds[arg] = { 'channel_id': channel_id,
                    'message_id':'',
                    'dict_user_table':{},
                    'sun': [],
                    'mon': [],
                    'tue': [],
                    'wed': [],
                    'thu': [],
                    'fri': [],
                    'sat': []
                  }
    
# Takes in the list of names and returns a nice string
def day_print(input_list):
    ret_str = ""

    for n,nick in enumerate(input_list):
        ret_str = ret_str + "    " + str(n+1) + ". " + nick + "\n"

    return ret_str

@client.event
async def on_ready():
    global guilds
    async for guild in client.fetch_guilds(limit=150):
        init_guilds(guild.id, None)

@client.event
async def on_guild_join(guild):
    global guilds
    
    guilds[guild.id] = {'channel_id':None,
                    'message_id':'',
                    'dict_user_table':{},
                    'sun': [],
                    'mon': [],
                    'tue': [],
                    'wed': [],
                    'thu': [],
                    'fri': [],
                    'sat': []
                  }

@client.event
async def on_guild_remove(guild):
    global guilds
    
    guilds.pop(guild.id,None)

@client.event
async def on_raw_reaction_add(payload):
    global guilds
    global day_emotes
    guild_id = payload.guild_id
    channel = client.get_channel(guilds[guild_id]['channel_id'])
    message_id = guilds[guild_id]['message_id']
    if (channel is None) or (message_id == ''):
        return
    
    if (channel.id == guilds[guild_id]['channel_id']) and (payload.message_id == message_id):
        day = payload.emoji.name
        if day in day_emotes:
            guilds[guild_id][day].append(payload.member.nick)

        guilds[guild_id]['dict_user_table'][payload.user_id] = payload.member.nick

@client.event
async def on_raw_reaction_remove(payload):
    global guilds
    global day_emotes
    guild_id  = payload.guild_id
    channel = client.get_channel(guilds[guild_id]['channel_id'])
    message_id = guilds[guild_id]['message_id']
    user_list = guilds[guild_id]['dict_user_table'].keys()

    if (channel is None) or (message_id == ''):
        return

    if (channel.id == guilds[guild_id]['channel_id']) and (payload.message_id == message_id):
        # Check if the user exists in the dict
        user = payload.user_id
        if user in user_list:
            # Get the user's nickname
            user_nick = guilds[guild_id]['dict_user_table'][payload.user_id]
        else:
          # User does not exist
          return

        # Remove user from day list if possible
        day = payload.emoji.name
        if day in day_emotes:
            day_list = guilds[guild_id][day]

        # if user_nick in day_list:
        day_list.remove(user_nick)

@client.event
async def on_message(message):
    global guilds
    global day_emotes
    guild_id = message.guild.id

    if '~.watch_channel' in message.content.lower():
        str_input = message.content.lower()
        guilds[guild_id]['channel_id'] = int(str_input[16:])
    elif '~.watch_message' in message.content.lower():
        temp_id = guilds[guild_id]['channel_id']
        # reinitialize the guilds entry
        init_guilds(guild_id, temp_id)
        str_input = message.content.lower()
        guilds[guild_id]['message_id'] = int(str_input[16:])
    elif '~.hasi' in message.content.lower():
        str_input = message.content.lower()[7:]

        # Formulate the string
        if str_input in day_emotes:
            str_data = "```CSS\n#" + str_input.capitalize() + ": \n" + day_print(guilds[guild_id][str_input]) + "```"
        else:
            # Default: send lists for every day
            str_data = "```CSS\n#Sun:\n{}\n#Mon:\n{}\n#Tue:\n{}\n#Wed:\n{}\n#Thu:\n{}\n#Fri:\n{}\n#Sat:\n{}```".format(day_print(guilds[guild_id]['sun']),
                                                           day_print(guilds[guild_id]['mon']),
                                                           day_print(guilds[guild_id]['tue']),
                                                           day_print(guilds[guild_id]['wed']),
                                                           day_print(guilds[guild_id]['thu']),
                                                           day_print(guilds[guild_id]['fri']),
                                                           day_print(guilds[guild_id]['sat']))
        # Send the string
        await message.channel.send(str_data)
    elif '~.roll_echo' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[12:]
        attempts,total_stat = get_echo_30()
        
        resp = "It took {} attempts! The total stat is: {}".format(attempts,total_stat)
        
        await message.channel.send(str(resp))
    
    elif '~.print_guilds' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[15:]
        await message.channel.send(str(guilds))
    elif '~.search items' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[15:]

        main_url = 'https://api.mabibase.com/items/search/name/{}'.format(str_input)
        response = requests.get(url = main_url)
        item_id = response.json()['data']['items'][0]['id']

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
            # import pdb; pdb.set_trace();
            lst_rolls = df_final['random_product'][0].split(";")
            for str_ in lst_rolls:
                pos_comma = str_.find(",")
                df_final[str_[:pos_comma]] = str_[pos_comma+1:]
                
        except Exception as ex:
            print(ex)


        df_final = df_final.drop(columns=['xml_string','set_effects','random_product'], axis=1, errors='ignore')
        
        # Get the icon
        # url = 'https://api.mabibase.com/icon/item/{}'.format(item_id)
        # response3 = requests.get(url = url)
        # import pdb; pdb.set_trace();
        obj_embed = discord.Embed(title=df['name'][0], description=df['description'][0])
        # picture = discord.Embed(io.BytesIO(response3.content))
        url = "https://api.mabibase.com/icon/item/" + str(item_id)
        obj_embed.set_image(url=url)
        
        # import pdb; pdb.set_trace();
        
        str_final = "```\n" + str(df_final.transpose()) + "\n```"
        the_link = "https://mabibase.com/item/" + str(item_id)
        await message.channel.send(embed=obj_embed, content=the_link)
        await message.channel.send(content=str_final)
    elif '~.search es' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[12:]
        
        main_url = 'https://api.mabibase.com/enchants/search?q=name,{}'.format(str_input)
        response = requests.get(url = main_url)
        
        # import pdb; pdb.set_trace();
        
        df = pd.DataFrame([response.json()['data']['enchants'][0]])
        
        try:
            # import pdb; pdb.set_trace();
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
