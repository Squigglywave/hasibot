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

