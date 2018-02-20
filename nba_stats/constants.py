# TODO: Convert all these URLs to parameter dicts...
NBA_BASE_URL = "http://stats.nba.com/stats/"

TEAM_INFO_BASE_URL = ("teaminfocommon?LeagueID=00&SeasonType=Regular+Season&"
                      "TeamID=1610612{id}&season={season}")

PLAYER_INFO_URL = "commonplayerinfo?LeagueID=00&PlayerID={player_id}&SeasonType={season_type}"
# Not exactly sure how to check/determine the season type
SUMMARY_URL = "boxscoresummaryv2?GameID={game_id}"

TRADITIONAL_BOX_URL = ("boxscoretraditionalv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=0"
                      "&Season={season}&SeasonType={season_type}&StartPeriod=1&StartRange=0")

ADVANCED_BOX_URL = ("boxscoreadvancedv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=0&Se"
                    "ason={season}&SeasonType={season_type}&StartPeriod=1&StartRange=0")

MISC_BOX_URL = ("boxscoremiscv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=0&Season="
                "{season}&SeasonType={season_type}&StartPeriod=1&StartRange=0")

SCORING_BOX_URL = ("boxscorescoringv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=0&Season="
                   "{season}&SeasonType={season_type}&StartPeriod=1&StartRange=0")

USAGE_BOX_URL = ("boxscoreusagev2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=0&Season={season}"
                 "&SeasonType={season_type}&StartPeriod=1&StartRange=0")

PLAYER_TRACK_BOX_URL = ("boxscoreplayertrackv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&Ra"
                        "ngeType=0&Season={season}&SeasonType={season_type}&StartPeriod=1&StartRang"
                        "e=0")

FOUR_FACTORS_BOX_URL = ("boxscorefourfactorsv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&Ra"
                        "ngeType=0&Season={season}&SeasonType={season_type}&StartPeriod=1&StartRang"
                        "e=0")

HUSTLE_STATS_BOX_URL = ("hustlestatsboxscore?EndPeriod=10&EndRange=1000000000&GameID={game_id}&Ra"
                        "ngeType=0&Season={season}&SeasonType={season_type}&StartPeriod=1&StartRang"
                        "e=0")

PLAYER_CAREER_STATS_ENDPOINT = 'playercareerstats'
PLAYER_CAREER_STATS_PARAMS = {'PerMode': None,
                              'PlayerID': None,
                              'LeagueID': "00"}

TEAM_SEASONS_ENDPOINT = 'teamyearbyyearstats'
TEAM_SEASONS_PARMS = {'TeamID': None,
                      'LeagueID': '00',
                      'SeasonType': None,
                      'PerMode': None}


TEAM_LIST_ENDPOINT = 'commonteamyears'
TEAM_DETAILS_ENDPOINT = 'teamdetails'
TEAM_ROSTER_ENDPOINT = 'commonteamroster'

SHOTCHART_ENDPOINT = "shotchartdetail"
SHOTCHART_PARAMS = {'PlayerID': None,
                    'TeamID': 0,
                    'GameID': '',
                    'LeagueID': '00',
                    'Season': None,
                    'SeasonType': None,
                    'Outcome': '',
                    'Location': '',
                    'Month': 0,
                    'SeasonSegment': '',
                    'DateFrom': '',
                    'DateTo': '',
                    'OpponentTeamID': 0,
                    'VsConference': '',
                    'VsDivision': '',
                    'PlayerPosition': '',
                    'GameSegment': '',
                    'Period': 0,
                    'LastNGames': 0,
                    'AheadBehind': '',
                    'ContextMeasure': 'FGM',
                    'ClutchTime': '',
                    'RookieYear': ''}

PLAYER_GENERAL_SPLITS_ENDPOINT = 'playerdashboardbygeneralsplits'
PLAYER_SHOOTING_SPLITS_ENDPOINT = 'playerdashboardbyshootingsplits'

GENERAL_SPLITS_PARMS = {"MeasureType": None,
                                "PerMode": None,
                                "PlusMinus": "N",
                                "PaceAdjust": "N",
                                "Rank": "N",
                                "LeagueID": "00",
                                "Season": None,
                                "SeasonType": None,
                                "PORound": "",
                                "Outcome": "",
                                "Location": "",
                                "Month": 0,
                                "SeasonSegment": "",
                                "DateFrom": "",
                                "DateTo": "",
                                "OpponentTeamID": 0,
                                "VsConference": "",
                                "VsDivision": "",
                                "GameSegment": "",
                                "Period": 0,
                                "ShotClockRange": "",
                                "LastNGames": 0}

TEAM_GEN_SPLITS_ENDPOINT = 'teamdashboardbygeneralsplits'
TEAM_SHOOTING_SPLITS_ENDPOINT = 'teamdashboardbyshootingsplits'

PLAYER_SHOOTING_SPLITS_PARMS = GENERAL_SPLITS_PARMS

PLAYER_TRACKING_ENDPOINTS = {'Shots': 'playerdashptshots', 'Rebounds': 'playerdashptreb',
                             'Passes': 'playerdashptpass', 'Defense': 'playerdashptshotdefend'}

PLAYER_TRACKING_PARMS = {"PerMode": None,
                         "LeagueID": "00",
                         "Season": None,
                         "SeasonType": None,
                         "PlayerID": None,
                         "TeamID": 0,
                         "Outcome": "",
                         "Location": "",
                         "Month": 0,
                         "SeasonSegment": "",
                         "DateFrom": "",
                         "DateTo": "",
                         "OpponentTeamID": 0,
                         "VsConference": "",
                         "VsDivision": "",
                         "GameSegment": "",
                         "Period": 0,
                         "LastNGames": 0}

LEAGUE_PLAYER_TRACKING_ENDPOINT = "leaguedashptstats"
LEAUGE_PT_PARMS = {'College': "",
                   'Conference': "",
                   'Country': "",
                   'DateFrom': "",
                   'DateTo': "",
                   'Division': "",
                   'DraftPick': "",
                   'DraftYear': "",
                   'GameScope': "",
                   'Height': "",
                   'LastNGames': 0,
                   'LeagueID': "00",
                   'Location': "",
                   'Month': 0,
                   'OpponentTeamID': 0,
                   'Outcome': "",
                   'PORound': 0,
                   'PerMode': None,
                   'PlayerExperience': "",
                   'PlayerOrTeam': "Player",
                   'PlayerPosition': "",
                   'PtMeasureType': None,
                   'Season': None,
                   'SeasonSegment': "",
                   'SeasonType': None,
                   'StarterBench': "",
                   'TeamID': 0,
                   'VsConference': "",
                   'VsDivision': "",
                   'Weight': ""}

SPEED_DISTANCE = 'SpeedDistance'
REBOUNDING = 'Rebounding'
POSSESSIONS = 'Possessions'
CATCH_SHOOT = 'CatchShoot'
PULLUP_SHOT = 'PullUpShot'
DEFENSE = 'Defense'
DRIVES = 'Drives'
PASSING = 'Passing'
ELBOW_TOUCH = 'ElbowTouch'
POST_TOUCH = 'PostTouch'
PAINT_TOUCH = 'PaintTouch'
EFFICIENCY = 'Efficiency'


PT_MEASURE_TYPES = [SPEED_DISTANCE,
                    REBOUNDING,
                    POSSESSIONS,
                    CATCH_SHOOT,
                    PULLUP_SHOT,
                    DEFENSE,
                    DRIVES,
                    PASSING,
                    ELBOW_TOUCH,
                    POST_TOUCH,
                    PAINT_TOUCH,
                    EFFICIENCY]

PBP_URL = ("playbyplayv2?EndPeriod=10&EndRange=1000000000&GameID={game_id}&RangeType=2&Season={season}&SeasonType"
           "={season_type}&StartPeriod=1&StartRange=0")

# .format(split, season_str, season_type)
SORTABLE_PLAYER_STATS_URL = ("leaguedashplayerstats?College=&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick"
                             "=&DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&Location=&MeasureTy"
                             "pe=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode={split}&Period=0"
                             "&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season={season_str}&SeasonSegment=&"
                             "SeasonType={season_type}&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision="
                             "&Weight=")

# .format(split, season_str, season_type)
SORTABLE_TEAM_STATS_URL = ("leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division=&GameScope=&GameSegment=&LastNGa"
                           "mes=0&LeagueID=00&Location=&MeasureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&Pa"
                           "ceAdjust=N&PerMode={split}&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Se"
                           "ason={season_str}&SeasonSegment=&SeasonType={season_type}&ShotClockRange=&StarterBench=&Tea"
                           "mID=0&VsConference=&VsDivision=")

IGNORE_SEASON_TYPES = ["Rankings", "College"]

HEADERS = {'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/45.0.2454.101 Safari/537.36'),
           'Referer': "http://stats.nba.com/scores"}

MONTHS = {'jan': 1,
          'feb': 2,
          'mar': 3,
          'april': 4,
          'may': 5,
          'june': 6,
          'jul': 7,
          'aug': 8,
          'sep': 9,
          'oct': 10,
          'nov': 11,
          'dec': 12,
          'january': 1,
          'february': 2,
          'march': 3,
          'july': 7,
          'august': 8,
          'september': 9,
          'october': 10,
          'november': 11,
          'december': 12}

PLAYER_INDEX_URL = "http://stats.nba.com/stats/commonallplayers?IsOnlyCurrentSeason=0&LeagueID=00&Season=2016-17"
COACH_INDEX_URL = "http://www.basketball-reference.com/coaches/NBA_stats.html"
# %season, season_type
PLAYER_SORTABLE_ADVANCED_URL = ("http://stats.nba.com/stats/leaguedashplayerstats?College="
                                "&Conference=&Country=&DateFrom=&DateTo=&Division=&DraftPick="
                                "&DraftYear=&GameScope=&GameSegment=&Height=&LastNGames=0"
                                "&LeagueID=00&Location=&MeasureType=Advanced&Month=0"
                                "&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N"
                                "&PerMode=Totals&Period=0&PlayerExperience=&PlayerPosition="
                                "&PlusMinus=N&Rank=N&Season={season}&SeasonSegment="
                                "&SeasonType={seasontype}&ShotClockRange=&StarterBench=&TeamID=0&"
                                "VsConference=&VsDivision=&Weight=")
# %player_id, season_str, season_type
PLAYER_ADVANCED_STATS_URL = ("http://stats.nba.com/stats/playerdashboardbygeneralsplits?DateFrom=&DateTo=&GameSegment=&"
                             "LastNGames=0&LeagueID=00&Location=&MeasureType=Advanced&Month=0&OpponentTeamID=0&Outcome="
                             "&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0&PlayerID=%s&PlusMinus=N&Rank=N&Season=%s"
                             "&SeasonSegment=&SeasonType=%s&ShotClockRange=&VsConference=&VsDivision=")
PLAYER_STANDARD_URL = ("http://stats.nba.com/stats/playercareerstats?LeagueID=00"
                       "&PerMode={permode}&PlayerID={playerid}")

TEAM_SEASON_DATA_URL = ("http://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateT"
                        "o=&Division=&GameScope=&GameSegment=&LastNGames=0&LeagueID=00&Location=&Me"
                        "asureType=Base&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&Pe"
                        "rMode={split}&Period=0&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank="
                        "N&Season={season}&SeasonSegment=&SeasonType={seasontype}&ShotClockRange=&S"
                        "tarterBench=&TeamID=0&VsConference=&VsDivision=")

TEAM_ADVANCED_DATA_URL = ("http://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&Dat"
                          "eTo=&Division=&GameScope=&GameSegment=&LastNGames=0&LeagueID=00&Location"
                          "=&MeasureType=Advanced&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceA"
                          "djust=N&PerMode=Totals&Period=0&PlayerExperience=&PlayerPosition=&PlusMi"
                          "nus=N&Rank=N&Season={season}&SeasonSegment=&SeasonType={seasontype}&Shot"
                          "ClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=")
# $ (month, day, year)
DATE_SCOREBOARD_URL = "http://stats.nba.com/stats/scoreboardV2?DayOffset=0&LeagueID=00&gameDate={month}%2F{day}%2F{year}"

BBREF_BASE_URL = "http://www.basketball-reference.com/"
BBREF_NBA_COACH_LIST = "coaches/NBA_stats.html"
BBREF_COACH_URL = "coaches/{coachid}.html"
BBREF_COACH_SEASON_DATA_FIELDS = ['team_id', 'g', 'wins', 'losses', 'win_loss_pct', 'g_playoffs',
                                  'wins_playoffs', 'losses_playoffs', 'win_loss_pct_playoffs']

INJURIES_URL = "http://www.rotoworld.com/teams/injuries/nba/all/"
SALARIES_URL = "http://hoopshype.com/salaries/players/"
CONTRACT_OPTIONS = {'pl': 'player',
                    'tm': 'team',
                    'et': 'early termination'}
BBREF_CONTRACTS_ENDPOINT = "contracts/players.html"
ROTOWORLD_CONTRACTS_BASE_URL = "http://www.rotoworld.com/teams/contracts/nba/"
ROTOWORLD_TEAM_CONTRACT_SUFFIXES = {'PHI': "phi/76ers",
                                    'MIL': "mlw/bucks",
                                    'CHI': "chi/bulls",
                                    'CLE': "cle/cavaliers",
                                    'BOS': "bos/celtics",
                                    'LAC': "lac/clippers",
                                    'MEM': "mem/grizzlies",
                                    'ATL': "atl/hawks",
                                    'MIA': "mia/heat",
                                    'CHA': "cha/hornets",
                                    'UTA': "uta/jazz",
                                    'SAC': "sac/kings",
                                    'NYK': "ny/knicks",
                                    'LAL': "lak/lakers",
                                    'ORL': "orl/magic",
                                    'DAL': "dal/mavericks",
                                    'BKN': "bkn/nets",
                                    'DEN': "den/nuggets",
                                    'IND': "ind/pacers",
                                    'NOP': "no/pelicans",
                                    'DET': "det/pistons",
                                    'TOR': "tor/raptors",
                                    'HOU': "hou/rockets",
                                    'SAS': "sa/spurs",
                                    'PHX': "pho/suns",
                                    'OKC': "okc/thunder",
                                    'MIN': "min/timberwolves",
                                    'POR': "por/trail-blazers",
                                    'GSW': "gs/warriors",
                                    'WAS': "was/wizards"}

NBA_TRANSACTION_ENDPOINT = "http://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json"

BBREF_DRAFT_ENDPOINT = "draft/NBA_{year}.html"

TOTALS = "Totals"
PER_GAME = "PerGame"
MINUTES_PER = "MinutesPer"
PER_48 = "Per 48"
PER_40 = "Per 40"
PER_36 = "Per 36"
PER_MINUTE = "PerMinute"
PER_POSSESSION = "PerPossession"
PER_PLAY = "PerPlay"
PER_100_POSSESSIONS = "Per100Possessions"
PER_100_PLAYS = "Per100Plays"
PER_MODES = [TOTALS, PER_GAME, MINUTES_PER, PER_48, PER_40, PER_36, PER_MINUTE,
             PER_POSSESSION, PER_PLAY, PER_100_POSSESSIONS, PER_100_PLAYS]

BASE = "Base"
ADVANCED = "Advanced"
MISC = "Misc"
FOUR_FACTORS = "Four Factors"
SCORING = "Scoring"
OPPONENT = "Opponent"
USAGE = "Usage"
DEFENSE = "Defense"
MEASURE_TYPES = [BASE, ADVANCED, MISC, FOUR_FACTORS, SCORING,
                 OPPONENT, USAGE, DEFENSE]

REGULAR_SEASON = "Regular Season"
PLAYOFFS = "Playoffs"
SEASON_TYPES = [REGULAR_SEASON, PLAYOFFS]

GROUP_SETS = {'Overall': 'overall',
              'Location': 'location',
              'Month': 'month',
              'Pre/Post All-Star': "season_segment",
              'Starting Position': "starter_bench",
              'Wins/Losses': 'outcome'}
GROUP_VALUES = {'Home': "Home",
                'Road': "Road",
                'Pre All-Star': "Pre All-Star",
                'Post All-Star': "Post All-Star",
                'Bench': "Bench",
                'Starters': "Starters",
                "Wins": "W",
                'Losses': 'L'}
SET_TO_VALUES_MAP = {'Overall': ["CUR_SEASON"],
                     'Location': ["Home", "Road"],
                     'Month': [str(x) for x in range(13)],
                     'Pre/Post All-Star': ["Pre All-Star", "Post All-Star"],
                     'Starting Position': ["Bench", "Starters"],
                     'Wins/Losses': ["Wins", "Losses"]}

REVERSE_MONTH_MAP = {'1': 'October',
                     '5': 'February',
                     '9': 'June',
                     '0': 'All',
                     '10': 'July',
                     '12': 'September',
                     '2': 'November',
                     '3': 'December',
                     '11': 'August',
                     '7': 'April',
                     '6': 'March',
                     '4': 'January',
                     '8': 'May'}
GROUP_VALUES.update(REVERSE_MONTH_MAP)

ON_OFF_PARAMS = {'TeamID': None,
                 'Season': None,
                 'SeasonType': None,
                 'MeasureType': None,
                 'PerMode': None,
                 'VsDivision': "",
                 'PaceAdjust': 'N',
                 'Outcome': "",
                 'GameSegment': "",
                 'VsConference': "",
                 'Month': 0,
                 'LeagueID': '00',
                 'DateFrom': "",
                 'PlusMinus': 'N',
                 'SeasonSegment': "",
                 'LastNGames': 0,
                 'Location': "",
                 'OpponentTeamID': 0,
                 'Period': 0,
                 'DateTo': "",
                 'Rank': 'N'}

TRANSACTION_COLORS = {'Claimed': "9900cc",  # Purple
                      'Drafted': "#009933",  # Green
                      "Re-signed": "#ff66cc",  # Pink
                      "Released": "ff0000",  # Red
                      'Retired': "#000000",  # Black
                      'Signed': "#1a1aff",  # Blue
                      'Sold': "#999999",  # Gray
                      'Suspended': "#00ffff",  # Light blue
                      'Traded': "ffff00",  # Yellow
                      'Waived': "ff9900"}  # Orange