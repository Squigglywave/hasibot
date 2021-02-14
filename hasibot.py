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
intents = discord.Intents.all()
intents.members = True
client = discord.Client(intents=intents)

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
def day_print(guild_id, day):
    global guilds
    ret_str = ""

    lst_names = guilds[guild_id][day]

    for n,user_id in enumerate(lst_names):
        user = client.get_guild(guild_id).get_member(user_id)
        if user.nick is not None:
            name = user.nick
        else:
            name = user.name
        ret_str = ret_str + "    " + str(n+1) + ". " + name + "\n"

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
            guilds[guild_id][day].append(payload.member.id)

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
        user = payload.user_id

        day = payload.emoji.name
        if day in day_emotes:
            day_list = guilds[guild_id][day]

        day_list.remove(user)

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
    elif '~.update_ut' in message.content.lower():
        lst_members = client.get_guild(guild_id).members
        
        for member in lst_members:
            name =  member.nick
            if name is None:
                name = member.name
        
            guilds[guild_id]['dict_user_table'][name.lower()] = member.id
        await message.channel.send('User Table Updated!')
    elif '~.load_id' in message.content.lower():
        str_input = message.content.lower()[10:]

        day = str_input[:3]
        str_input = str_input[4:]
     
        if day in day_emotes:
            lst_ids = eval(str_input)
            lst_guild_ids = [member.id for member in client.get_guild(guild_id).members]
            
            set1 = set(lst_guild_ids)
            set2 = set(lst_ids)
            
            bad_diff = set2-set1
            
            lst_bad_items = []
            while len(bad_diff) > 0:
                bad_item = bad_diff.pop()
                lst_bad_items.append(bad_item)
                lst_ids.remove(bad_item)
                
            # list(set(lst_guild_ids) - set(lst_ids))
            
            guilds[guild_id][day] = lst_ids

        await message.channel.send('Loaded ids for day: {}, Ids failed: {}'.format(day,lst_bad_items))
    elif '~.load' in message.content.lower():
        str_input = message.content.lower()[7:]
        
        day = str_input[:3]
        str_input = str_input[4:]

        if day in day_emotes:
            lst_names = eval(str_input)
            
            guilds[guild_id][day] = []
            for name in lst_names:
                if name in guilds[guild_id]['dict_user_table'].keys():
                    user_id = guilds[guild_id]['dict_user_table'][name.lower()]
                    guilds[guild_id][day].append(user_id)
                else:
                    await message.channel.send('Name {} missing in ut'.format(name))

        await message.channel.send('Loaded ' + day)
        
    elif '~.hasi' in message.content.lower():
        str_input = message.content.lower()[7:]

        # Formulate the string
        if str_input in day_emotes:
            str_data = "```CSS\n#" + str_input.capitalize() + ": \n" + day_print(guild_id, str_input) + "```"
        else:
            # Default: send lists for every day
            str_data = "```CSS\n#Sun:\n{}\n#Mon:\n{}\n#Tue:\n{}\n#Wed:\n{}\n#Thu:\n{}\n#Fri:\n{}\n#Sat:\n{}```".format(day_print(guild_id, 'sun'),
                                                           day_print(guild_id,'mon'),
                                                           day_print(guild_id,'tue'),
                                                           day_print(guild_id,'wed'),
                                                           day_print(guild_id,'thu'),
                                                           day_print(guild_id,'fri'),
                                                           day_print(guild_id,'sat'))
        # Send the string
        await message.channel.send(str_data)
    elif '~.roll_echo' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[12:]
        attempts,total_stat = get_echo_30()
        
        resp = "It took {} attempts! The total stat is: {}".format(attempts,total_stat)
        
        await message.channel.send(str(resp))
    
    elif '~.print_info' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[13:]
        
        df_final = pd.DataFrame()
        df_final2 = pd.DataFrame()
        
        for guild in guilds.keys():
            df = pd.DataFrame([guilds[guild]])
            df['guild'] = guild
            df['guild_name'] = client.get_guild(guild).name
            df_final2 = pd.concat([df_final2,df])
            df['sun'] = len(df['sun'][0])
            df['mon'] = len(df['mon'][0])
            df['tue'] = len(df['tue'][0])
            df['wed'] = len(df['wed'][0])
            df['thu'] = len(df['thu'][0])
            df['fri'] = len(df['fri'][0])
            df['sat'] = len(df['sat'][0])
            df_final = pd.concat([df_final, df])

        cols = ['guild','guild_name','channel_id','message_id','sun','mon','tue','wed','thu','fri','sat']
        df_final = df_final[cols]
        df_final2 = df_final2[cols]

        lst_args = str_input.split(" ")


        # import pdb; pdb.set_trace();
        if lst_args[0].lower() == 'gid' and len(lst_args) == 2:
            df_final = df_final[df_final['guild'] == int(lst_args[1])]
        elif lst_args[0].lower() == 'gid' and len(lst_args) == 3:
            df_final2 = df_final2[df_final['guild'] == int(lst_args[1])]
            df_final2 = df_final2[lst_args[2]][0]
            df_final = df_final2
        
        if type(df_final) == list:
            str_final = "```\n" + str(df_final) + "\n```"
        else:
            str_final = "```\n" + str(df_final.transpose()) + "\n```"
        
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
