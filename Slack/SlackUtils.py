import numpy    as np
import pandas   as pd
import datetime as dt

import time
import hashlib
import slack_sdk
import shutil
import json

from pathlib          import Path
from slack_sdk.errors import SlackApiError

#############################################################################################
#############################################################################################
def GetUsersInfo(oClient, bHash_users, HashString, pUsersFile):
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

    dUsers.to_csv(pUsersFile, index=False)
    
    return dUsers    
#############################################################################################
#############################################################################################
def GetChannelsInfo(oClient, bHashChannels, HashString, pChannelsFile):
    lChannelKeys = ['id', 'name']
    lChannels    = []

    bIsDone   = False
    sNextPage = ''
    while bIsDone == False:
        oPublicChannels = oClient.conversations_list(limit=100, cursor=sNextPage) #-- get response
        lPublicChannels = oPublicChannels.data['channels']                        #-- get channels

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
        dChannels['FileName'] = dChannels.apply(lambda x: f"{x['id']}_{x['ChannelHashID']}.csv", axis=1)
    else:
        dChannels['FileName'] = dChannels.apply(lambda x: f"{x['id']}_{x['name']}.csv",          axis=1)

    dChannels.to_csv(pChannelsFile, index=False)
    
    return dChannels
#############################################################################################
#############################################################################################
def GetChannelHistory(oClient, dChannel, bHash_channels, pPublicChannelsFolder, bInclude_text, begin_date_ts):
    lMessageKeys = ['type', 'subtype', 'ts', 'user', 'text']

    id           = dChannel['id']
    pChannelFile = pPublicChannelsFolder / dChannel['FileName']

    lChannelHistory  = []
    bIsDone          = False
    sNextPage        = ''
    #-- Get history:
    while bIsDone == False:
        try:
            oHistory  = oClient.conversations_history(channel=id, limit=1000, cursor=sNextPage, oldest=begin_date_ts) #-- get response
        except SlackApiError as oError:
            #-- Rate error --> wait for 3 seconds and continue
            print('SLEEP!', end='')
            time.sleep(1)
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
    dChannelHistory.to_csv(pChannelFile, index=False)

    return dChannelHistory

#############################################################################################
#############################################################################################
def SaveChannelsHistory(oClient, dChannels, pPublicChannelsFolder, bHash_channels, bInclude_text, runtimeLimit=float('inf'), sBeginDate='01-01-2019', bOverride=False):
    nChannels     = dChannels.shape[0]
    begin_date    = dt.datetime.strptime(sBeginDate, "%m-%d-%Y").date()
    begin_date_ts = dt.datetime.timestamp(dt.datetime.combine(begin_date, dt.time()))
    startTime     = time.time()
    bJob_done     = True

    print('This might take a while...')
    #-- for each channel:
    for ii, dChannel in dChannels.iterrows():
        #-- Break on time:
        if time.time() - startTime > runtimeLimit:
            bJob_done = False
            break
        print(f'\r{ii+1} / {nChannels} channels ', end='')

        pChannelFile = pPublicChannelsFolder / dChannel['FileName']
        if pChannelFile.exists() == True and bOverride == False:
            continue
        GetChannelHistory(oClient, dChannel, bHash_channels, pPublicChannelsFolder, bInclude_text, begin_date_ts)

    print('Done!')

    return bJob_done
#############################################################################################
#############################################################################################
def GetSlackData(dConfig):

    #-- Unpack configs:
    slack_clinet_token = dConfig    ['TOKEN']
    domain_name        = dConfig.get('DOMAIN_NAME',    'Your_Company_Name')
    hash_unique_str    = dConfig.get('HASH_UNIQUE_STR', 'AB!@3')
    bInclude_text      = dConfig.get('INCLUDE_TEXT',    False)
    bHash_channels     = dConfig.get('HASH_CHANNELS',   False)
    bHash_users        = dConfig.get('HASH_USERS',      True)
    runtime_limit      = dConfig.get('RUNTIME_LIMIT',   float('inf'))
    sBegin_date        = dConfig.get('BEGIN_DATE',      '01-01-2019')
    bOverride          = dConfig.get('OVERRIDE',        False)
    bZip               = dConfig.get('ZIP',             True)
    bDownload          = dConfig.get('DOWNLOAD',        True)

    #-- Files & folders
    FOLDER_PATH           = f'./{domain_name}SlackData'
    pFolder               = Path(FOLDER_PATH)
    pConfigFile           = pFolder / 'Config.json'
    pUsersFile            = pFolder / 'users.csv'
    pChannelsFile         = pFolder / 'channels.csv'
    pPublicChannelsFolder = pFolder / 'PublicChannels'

    pFolder              .mkdir(exist_ok=True)
    pPublicChannelsFolder.mkdir(exist_ok=True)

    #-- Write configs to file:
    dConfigTemp = dConfig.copy()
    dConfigTemp.pop('TOKEN')
    with open(pConfigFile, 'w') as oFile:
        json.dump(dConfigTemp, oFile, indent=4)

    #-- Hash function:
    def HashString(string):
        if pd.isna(string) == True:
            return np.nan
        else:
            return hashlib.sha256((string + hash_unique_str).encode()).hexdigest()

    #-- Get API client:
    oClient   = slack_sdk.WebClient(token=slack_clinet_token)

    dUsers    = GetUsersInfo   (oClient, bHash_users,    HashString, pUsersFile   ) #-- get user list
    dChannels = GetChannelsInfo(oClient, bHash_channels, HashString, pChannelsFile) #-- get channel list

    #-- Save channels history:
    bJob_done = SaveChannelsHistory(
        oClient,
        dChannels,
        pPublicChannelsFolder,
        bHash_channels,
        bInclude_text,
        runtime_limit,
        sBegin_date,
        bOverride
    )

    #-- Zip the output folder:
    if bZip == True:
        shutil.make_archive(f'{pFolder}', 'zip', pFolder)
    
    #-- Download from Colab:
    if bDownload == True and 'google.colab' in str(get_ipython()):
        from google.colab import files
        files.download(f'{pFolder}.zip')
        
    if bJob_done == True:
        print(f'''\n\n
            =================================================================================
            =================================================================================
            Job complete - well done!
            Please send the {pFolder}.zip file to get.report@kynn.ai and results will follow
            =================================================================================
            =================================================================================
        \n\n''')

    return dUsers, dChannels
#############################################################################################
#############################################################################################

