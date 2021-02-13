# Standard Library
import os

# Third Party Library
import requests
import discord
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()

guilds = {}

@client.event
async def on_ready():
    global guilds
    async for guild in client.fetch_guilds(limit=150):
        guilds[guild.id] = { 'message_id':'',
                             'dict_user_table':{},
                             'sunday': [],
                             'monday': [],
                             'tuesday': [],
                             'wednesday': [],
                             'thursday': [],
                             'friday': [],
                             'saturday': []
                           }

@client.event
async def on_raw_reaction_add(payload):
    global guilds
    guild_id = payload.guild_id

    if payload.message_id == guilds[guild_id]['message_id']:
        if payload.emoji.name == 'sun':
            guilds[guild_id]['sunday'].append(payload.member.nick)
        elif payload.emoji.name == 'mon':
            guilds[guild_id]['monday'].append(payload.member.nick)
        elif payload.emoji.name == 'tue':
            guilds[guild_id]['tuesday'].append(payload.member.nick)
        elif payload.emoji.name == 'wed':
            guilds[guild_id]['wednesday'].append(payload.member.nick)
        elif payload.emoji.name == 'thu':
            guilds[guild_id]['thursday'].append(payload.member.nick)
        elif payload.emoji.name == 'fri':
            guilds[guild_id]['friday'].append(payload.member.nick)
        elif payload.emoji.name == 'sat':
            guilds[guild_id]['saturday'].append(payload.member.nick)
        guilds[guild_id]['dict_user_table'][payload.user_id] = payload.member.nick

@client.event
async def on_raw_reaction_remove(payload):
    global guilds
    guild_id = payload.guild_id

    if payload.message_id == guilds[guild_id]['message_id']:
        if payload.emoji.name == 'sun':
            guilds[guild_id]['sunday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'mon':
            guilds[guild_id]['monday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'tue':
            guilds[guild_id]['tuesday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'wed':
            guilds[guild_id]['wednesday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'thu':
            guilds[guild_id]['thursday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'fri':
            guilds[guild_id]['friday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])
        elif payload.emoji.name == 'sat':
            guilds[guild_id]['saturday'].remove(guilds[guild_id]['dict_user_table'][payload.user_id])

@client.event
async def on_message(message):
    global guilds
    guild_id = message.guild.id

    if '~.watch_message' in message.content.lower():
        guilds[guild_id] = { 'message_id':'',
                             'dict_user_table':{},
                             'sunday': [],
                             'monday': [],
                             'tuesday': [],
                             'wednesday': [],
                             'thursday': [],
                             'friday': [],
                             'saturday': []
                           }
        str_input = message.content.lower()
        guilds[guild_id]['message_id'] = int(str_input[16:])
    elif '~.hasi' in message.content.lower():
        str_input = message.content.lower()[7:]

        if str_input == 'all':
            str_data = "```Sun: {}\nMon: {}\nTue: {}\nWed: {}\nThu: {}\nFri: {}\nSat: {}```".format(guilds[guild_id]['sunday'],
                                                           guilds[guild_id]['monday'],
                                                           guilds[guild_id]['tuesday'],
                                                           guilds[guild_id]['wednesday'],
                                                           guilds[guild_id]['thursday'],
                                                           guilds[guild_id]['friday'],
                                                           guilds[guild_id]['saturday'])
            await message.channel.send(str_data)
        elif str_input == 'sun':
            await message.channel.send("```Sun: " + str(guilds[guild_id]['sunday']) + "```")
        elif str_input == 'mon':
            await message.channel.send("```Mon: " + str(guilds[guild_id]['monday']) + "```")
        elif str_input == 'tue':
            await message.channel.send("```Tue: " + str(guilds[guild_id]['tuesday']) + "```")
        elif str_input == 'wed':
            await message.channel.send("```Wed: " + str(guilds[guild_id]['wednesday']) + "```")
        elif str_input == 'thu':
            await message.channel.send("```Thu: " + str(guilds[guild_id]['thursday']) + "```")
        elif str_input == 'fri':
            await message.channel.send("```Fri: " + str(guilds[guild_id]['friday']) + "```")
        elif str_input == 'sat':
            await message.channel.send("```Sat: " + str(guilds[guild_id]['saturday']) + "```")
    elif '~.search' in message.content.lower():
        str_input = message.content.lower()
        str_input = str_input[9:]

        url = 'https://api.mabibase.com/items/search/name/{}'.format(str_input)
        response = requests.get(url = url)
        item_id = response.json()['data']['items'][0]['id']

        url = 'https://api.mabibase.com/item/{}'.format(item_id)
        response2 = requests.get(url = url)

        await message.channel.send(response2.json()['data']['item'])

client.run(TOKEN)
