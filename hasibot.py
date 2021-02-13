# Standard Library
import os

# Third Party Library
import requests
import discord
from dotenv import load_dotenv

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
def init_guilds(arg):
    global guilds

    guilds[arg] = { 'message_id':'',
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
async def on_ready():
    global guilds
    async for guild in client.fetch_guilds(limit=150):
        init_guilds(guild.id)

@client.event
async def on_raw_reaction_add(payload):
    global guilds
    global day_emotes
    guild_id = payload.guild_id

    if payload.message_id == guilds[guild_id]['message_id']:
        day = payload.emoji.name
        if day in day_emotes == True:
            guilds[guild_id][day].append(payload.member.nick)

        guilds[guild_id]['dict_user_table'][payload.user_id] = payload.member.nick

@client.event
async def on_raw_reaction_remove(payload):
    global guilds
    global day_emotes
    guild_id  = payload.guild_id
    user_list = guilds[guild_id]['dict_user_table'][payload.user_id]

    if payload.message_id == guilds[guild_id]['message_id']:
        # Check if the user exists in the dict
        user = payload.user_id
        if user in user_list == True:
            # Get the user's nickname
            user_nick = guilds[guild_id]['dict_user_table'][payload.user_id]
        else
          # User does not exist
          return

        # Remove user from day list if possible
        day = payload.emoji.name
        if day in day_emotes == True:
            day_list = guilds[guild_id][day]

        if user_nick in day_list == True:
            day_list.remove(user_nick)

@client.event
async def on_message(message):
    global guilds
    global day_emotes
    guild_id = message.guild.id

    if '~.watch_message' in message.content.lower():
        # reinitialize the guilds entry
        init_guilds(guild_id)
        str_input = message.content.lower()
        guilds[guild_id]['message_id'] = int(str_input[16:])
    elif '~.hasi' in message.content.lower():
        str_input = message.content.lower()[7:]

        # Formulate the string
        if str_input in day_emotes == True:
            str_data = "```" + str_input + ": " + str(guilds[guild_id][str_input]) + "```"
        else
            # Default: send lists for every day
            str_data = "```Sun: {}\nMon: {}\nTue: {}\nWed: {}\nThu: {}\nFri: {}\nSat: {}```".format(guilds[guild_id]['sunday'],
                                                           guilds[guild_id]['mon'],
                                                           guilds[guild_id]['tue'],
                                                           guilds[guild_id]['wed'],
                                                           guilds[guild_id]['thu'],
                                                           guilds[guild_id]['fri'],
                                                           guilds[guild_id]['sat'])
        # Send the string
        await message.channel.send(str_data)
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