## CONFIGS: #########################################
dConfig = dict(
    #-- Fill this: -----------------------------------
    TOKEN           = 'xoxb-not-a-real-token-this-will-not-work', # <-- Paste here
    DOMAIN_NAME     = 'your-company-name',                        # <-- Write your company name
    HASH_UNIQUE_STR = 'AB!@3',                                    # <-- Write some string (anything) and store it (for reverse hashing) 
    #-------------------------------------------------

    INCLUDE_TEXT  = False,
    HASH_CHANNELS = False,
    HASH_USERS    = True,
    RUNTIME_LIMIT = float('inf'),
    # RUNTIME_LIMIT = 300,
    BEGIN_DATE    = '01-01-2019', #-- MM-DD-YYYY
    OVERRIDE      = False,
    ZIP           = True,
    DOWNLOAD      = False,
)
#####################################################

from SlackUtils import GetSlackData

dUsers, dChannels = GetSlackData(dConfig)