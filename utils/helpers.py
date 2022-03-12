def day_print(client, guild_id, lst_users):
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

def get_user(client, guild_id, user_id):
    '''
    Returns user's name given a user_id

    Arguments:
    - guild_id   string  the ID of the guild to fetch the guild members from
    - user_id    string  user_id

    Returns:
    - user       string  user's name
    '''
    user = client.get_guild(int(guild_id)).get_member(int(user_id))
    if user.nick is not None:
        name = user.nick
    else:
        name = user.name
            
    return name

def get_user_id(client, guild_id, username):
    user_id = ''
    lst_members = client.get_guild(int(guild_id)).members
    
    bool_found = True
    dict_ids = {}
    dict_nicks = {}
    for member in lst_members:
        if member.name not in dict_ids.keys() and member.name is not None:
            dict_ids[str(member.name).lower()] = member.id
        if member.nick not in dict_nicks.keys() and member.name is not None:
            dict_nicks[str(member.nick).lower()] = member.id
    
    if username in dict_ids.keys():
        user_id = dict_ids[username]  
    elif username in dict_nicks.keys():
        user_id = dict_nicks[username]
    else:
        bool_found = False
        user_id = "User id not found"    
    
    return user_id, bool_found

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

