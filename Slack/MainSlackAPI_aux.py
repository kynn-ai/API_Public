from xml import dom
import numpy  as np
import pandas as pd

import time
import hashlib
import slack_sdk
import shutil

from pathlib          import Path
from slack_sdk.errors import SlackApiError

#%%
#############################################################################################
#############################################################################################
def GetUsersData(oClient, bHash_users, HashString, pUsersFile):
    lUserKeys = ['id', 'first_name', 'last_name', 'real_name', 'email', 'deleted', 'is_bot']
    lUsers    = []

    bIsDone   = False
    sNextPage = ''
    while bIsDone == False:
        oUsersList = oClient.users_list(limit=100, cursor=sNextPage) #-- get response
        lUsersList = oUsersList.data['members']                      #-- get users

        #-- Extract keys:
        for dUser in lUsersList:
            lUser = []
            for key in lUserKeys:
                if   key in dUser:            lUser += [dUser[key]]
                elif key in dUser['profile']: lUser += [dUser['profile'][key]]
                else:                         lUser += [np.nan]

    #         #-- Skip bots:
    #         if lUser[0] == 'USLACKBOT' or lUser[-1] == True:
    #             continue

            lUsers += [lUser]

        #-- Get next page:
        sNextPage = oUsersList.data['response_metadata']['next_cursor']
        if sNextPage == '':
            bIsDone = True

    dUsers               = pd.DataFrame(lUsers, columns=lUserKeys)
    dUsers['UserHashID'] = dUsers['email'].apply(HashString)
    if bHash_users == True:
        dUsers.drop(columns=['first_name', 'last_name', 'real_name', 'email'], inplace=True)

    dUsers.to_csv(pUsersFile)
    
    return dUsers    
#############################################################################################
#############################################################################################

#%%
#############################################################################################
#############################################################################################
def GetChannelsData(oClient, bHashChannels, HashString, pChannelsFile):
    lChannelKeys = ['id', 'name']
    lChannels    = []

    bIsDone   = False
    sNextPage = ''
    while bIsDone == False:
        oPublicChannels = oClient.conversations_list(limit=100, cursor=sNextPage) #-- get response
        lPublicChannels = oPublicChannels.data['channels']                       #-- get channels

        #-- Extract keys:
        for dChannel in lPublicChannels:
            lChannels += [[dChannel[key] for key in lChannelKeys]]

        #-- Get next page:
        sNextPage = oPublicChannels.data['response_metadata']['next_cursor']
        if sNextPage == '':
            bIsDone = True

    dChannels = pd.DataFrame(lChannels, columns=lChannelKeys)
    dChannels['ChannelHashID'] = dChannels['name'].apply(HashString)
    if bHashChannels == True:
        dChannels.drop(columns=['name'], inplace=True)

    dChannels.to_csv(pChannelsFile)
    
    return dChannels
#############################################################################################
#############################################################################################

#%%
#############################################################################################
#############################################################################################
def SaveChannelsHistory(oClient, dChannels, bHash_channels, pPublicChannelsFolder, bInclude_text):
    nChannels    = dChannels.shape[0]
    lMessageKeys = ['type', 'subtype', 'ts', 'user', 'text']

    print('This might take a while...')
    #-- for each channel:
    for ii, dChannel in dChannels.iterrows():

        id           = dChannel['id']
        if bHash_channels == True:
            name = dChannel['ChannelHashID']
        else:
            name = dChannel['name']
        pChannelFile = pPublicChannelsFolder / f"{id}_{name}.csv"
        print(f'\r{ii+1} / {nChannels} channels ', end='')

        lChannelHistory  = []
        bIsDone          = False
        sNextPage        = ''
        #-- Get history:
        while bIsDone == False:
            try:
                oHistory  = oClient.conversations_history(channel=id, limit=100, cursor=sNextPage) #-- get response
            except SlackApiError as oError:
                #-- Rate error --> wait for 10 seconds and continue
                time.sleep(10)
                continue

            lMessages = oHistory.data['messages']                                                  #-- get messages

            #-- Extract keys:
            for dMessage in lMessages:
                lChannelHistory += [[dMessage.get(key, np.nan) for key in lMessageKeys]]

            #-- Get next page:
            if oHistory.data['has_more'] == True:
                sNextPage = oHistory.data['response_metadata']['next_cursor']
            else:
                bIsDone = True

        dChannelHistory = pd.DataFrame(lChannelHistory, columns=lMessageKeys)
        if bInclude_text == False:
            dChannelHistory.drop(columns=['text'], inplace=True)
        dChannelHistory.to_csv(pChannelFile)

    print('Done!')
#############################################################################################
#############################################################################################

#%%
#############################################################################################
#############################################################################################
def GetSlackData(
    slack_clinet_token,
    domain_name,
    hash_unique_str,
    bInclude_text,
    bHash_channels,
    bHash_users
):
    #-- Hash function:
    def HashString(string):
        if pd.isna(string) == True:
            return np.nan
        else:
            return hashlib.sha256((string + hash_unique_str).encode()).hexdigest()

    #-- Files & folders
    FOLDER_PATH           = f'./{domain_name}SlackData'
    pFolder               = Path(FOLDER_PATH)
    pUsersFile            = pFolder / 'users.csv'
    pChannelsFile         = pFolder / 'channels.csv'
    pPublicChannelsFolder = pFolder / 'PublicChannels'

    pFolder              .mkdir(exist_ok=True)
    pPublicChannelsFolder.mkdir(exist_ok=True)

    #-- Get API client:
    oClient = slack_sdk.WebClient(token=slack_clinet_token)

    dUsers    = GetUsersData   (oClient, bHash_users,    HashString, pUsersFile   ) #-- get user list
    dChannels = GetChannelsData(oClient, bHash_channels, HashString, pChannelsFile) #-- get channel list

    #-- Save channels history:
    SaveChannelsHistory(oClient, dChannels, bHash_channels, pPublicChannelsFolder, bInclude_text)

    #-- Zip the output folder:
    shutil.make_archive(f'{pFolder}', 'zip', pFolder)
    
    #-- Download from Colab:
    if 'google.colab' in str(get_ipython()):
        from google.colab import files

        files.download(f'{pFolder}.zip')

    return dUsers, dChannels
#############################################################################################
#############################################################################################

