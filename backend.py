import os, requests
import streamlit as st


from datetime import datetime
from zoneinfo import ZoneInfo
import statistics as stats
import pandas as pd




class CFBD:
    def __init__(self, api_key=None):
        self.api_key = st.secrets["CFBD_API_KEY"]
        self.base = "https://api.collegefootballdata.com"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
    
    def get(self, path, **params):
        r = requests.get(f"{self.base}{path}", headers=self.headers, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

    def pull_week(self, year, week, conference):
        games_dict = {}
        games = self.get("/games", year = year, week = week, conference = conference, classification = 'fbs')
        for game in games:
            games_dict[game['id']] = {k: v for k, v in game.items() if k != 'id'}
        return games_dict

    def pull_teams(self, year):
        r = requests.get(
            f"{self.base}/teams",
            headers=self.headers,
            params={"year": year},
        )
        r.raise_for_status()
        return r.json()
    def to_central(self, iso_str):
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo("America/Chicago"))
    
    def default_week(self):
        today = datetime.now(ZoneInfo("America/Chicago"))
        if (today.month == 9 and today.day < 8):
            default_week = 1
        elif (today.month == 9 and today.day < 13):
            default_week = 2
        elif (today.month == 9 and today.day < 20):
            default_week = 3
        elif (today.month == 9 and today.day < 27):
            default_week = 4
        elif (today.month == 10 and today.day < 4) or (today.month == 9 and today.day >= 27):
            default_week = 5
        elif (today.month == 10 and today.day < 11):
            default_week = 6
        elif (today.month == 10 and today.day < 18):
            default_week = 7
        elif (today.month == 10 and today.day < 25):
            default_week = 8
        elif (today.month == 11 and today.day < 1) or (today.month == 10 and today.day >= 25):
            default_week = 9
        elif (today.month == 11 and today.day < 8):
            default_week = 10
        elif (today.month == 11 and today.day < 15):
            default_week = 11
        elif (today.month == 11 and today.day < 22):
            default_week = 12
        elif (today.month == 11 and today.day < 29):
            default_week = 13
        else:
            default_week = 1
        return default_week
    def statisticsToDisplayPost(self, box, plays, homeTeam, awayTeam):
        plays = plays.copy()
        plays['ppa'] = pd.to_numeric(plays['ppa'], errors='coerce')
        # PPA
        PPAhome = next(t for t in box["teams"]["ppa"] if t["team"] == homeTeam)
        PPAaway = next(t for t in box["teams"]["ppa"] if t["team"] == awayTeam)
        PPAtotalHome = PPAhome['overall']['total']
        PPApassingHome = PPAhome['passing']['total']
        PPArushingHome = PPAhome['rushing']['total']
        PPAtotalAway = PPAaway['overall']['total']
        PPApassingAway = PPAaway['passing']['total']
        PPArushingAway = PPAaway['rushing']['total']
        # Success Rate
        SRhome = next(t for t in box["teams"]["successRates"] if t["team"] == homeTeam)
        SRaway = next(t for t in box["teams"]["successRates"] if t["team"] == awayTeam)
        SRhomeTotal = SRhome['overall']['total']
        SRawayTotal = SRaway['overall']['total']
        # Yards per play
        EXCLUDE_PLAY_TYPES = [
            # Kicking / punting
            'Kickoff',
            'Kickoff Return (Offense)',
            'Kickoff Return Touchdown',
            'Punt',
            'Punt Return',
            'Punt Return Touchdown',
            'Blocked Punt',
            'Blocked Punt Touchdown',
            'Field Goal Good',
            'Field Goal Missed',
            'Blocked Field Goal',
            'Blocked Field Goal Touchdown',
            'Missed Field Goal Return',
            'Missed Field Goal Return Touchdown',
            'Extra Point Good',
            'Extra Point Missed',
            'Blocked PAT',
            'Two Point Rush',
            'Two Point Pass',
            'Defensive 2pt Conversion',
            'Timeout',
            'Penalty',
            'End Period',
            'End of Half',
            'End of Game',
            'End of Regulation',
            'Uncategorized',
            'Placeholder',
            'Offensive 1pt Safety',
            'Defensive 1pt Safety',
        ]
        THIRD_DOWN_EXCLUDE = [t for t in EXCLUDE_PLAY_TYPES if t != 'Penalty']
        playsDfHome = plays[plays['offense'] == homeTeam]
        playsDfAway = plays[plays['offense'] == awayTeam]
        scrimmageHome = playsDfHome[~playsDfHome['playType'].isin(EXCLUDE_PLAY_TYPES)].copy()
        scrimmageAway = playsDfAway[~playsDfAway['playType'].isin(EXCLUDE_PLAY_TYPES)].copy()
        playsHome = len(scrimmageHome)
        playsAway = len(scrimmageAway)
        yardsHome = sum(scrimmageHome['yardsGained'])
        yardsAway = sum(scrimmageAway['yardsGained'])
        yardsPerPlayHome = yardsHome / playsHome if playsHome else None
        yardsPerPlayAway = yardsAway / playsAway if playsAway else None
        # Third down
        thirdDownHome = playsDfHome[~playsDfHome['playType'].isin(THIRD_DOWN_EXCLUDE)].copy()
        thirdDownAway = playsDfAway[~playsDfAway['playType'].isin(THIRD_DOWN_EXCLUDE)].copy()
        thirdDownPlaysHome = thirdDownHome[thirdDownHome['down'] == 3].copy()
        thirdDownPlaysAway = thirdDownAway[thirdDownAway['down'] == 3].copy()
        thirdDownPlaysHome = thirdDownPlaysHome[(thirdDownPlaysHome['playType'] != 'Penalty') | thirdDownPlaysHome['playText'].str.contains('1ST DOWN', case=False, na=False)].copy()
        thirdDownPlaysAway = thirdDownPlaysAway[(thirdDownPlaysAway['playType'] != 'Penalty') | thirdDownPlaysAway['playText'].str.contains('1ST DOWN', case=False, na=False)].copy()
        thirdDownPlaysHome['converted'] = ((thirdDownPlaysHome['yardsGained'] >= thirdDownPlaysHome['distance']) | thirdDownPlaysHome['playText'].str.contains('1ST DOWN', case=False, na=False)).astype(int)
        thirdDownPlaysAway['converted'] = ((thirdDownPlaysAway['yardsGained'] >= thirdDownPlaysAway['distance']) | thirdDownPlaysAway['playText'].str.contains('1ST DOWN', case=False, na=False)).astype(int)
        thirdDPhome = thirdDownPlaysHome['converted'].mean() if len(thirdDownPlaysHome) else None
        thirdDaway = thirdDownPlaysAway['converted'].mean() if len(thirdDownPlaysAway) else None
        # Explosives
        explosivesNumHome = sum(scrimmageHome['ppa'] > 2)
        explosivesNumAway = sum(scrimmageAway['ppa'] > 2)
        explosiveRateHome = explosivesNumHome / playsHome if playsHome else None
        explosiveRateAway = explosivesNumAway / playsAway if playsHome else None
        # Travesties
        travestiesNumHome = sum(scrimmageHome['ppa'] < -1.5)
        travestiesNumAway = sum(scrimmageAway['ppa'] < -1.5)
        travestiesRateHome = travestiesNumHome / playsHome if playsHome else None
        travestiesRateAway = travestiesNumAway / playsAway if playsHome else None


        return PPAtotalHome, PPApassingHome, PPArushingHome, PPAtotalAway, PPApassingAway, PPArushingAway, SRhomeTotal, SRawayTotal, thirdDPhome, thirdDaway, yardsPerPlayHome, yardsPerPlayAway, explosivesNumHome, explosivesNumAway, explosiveRateHome, explosiveRateAway, travestiesNumHome, travestiesNumAway, travestiesRateHome, travestiesRateAway


    def statisticsToDisplayLive(self, plays, homeTeam, awayTeam):
        plays = pd.DataFrame(plays)
        if plays.empty:
            return (None,) * 20
        plays = plays.copy()
        plays['ppa'] = pd.to_numeric(plays.get('ppa'), errors='coerce')
        plays['yardsGained'] = pd.to_numeric(plays.get('yardsGained'), errors='coerce')
        plays['distance'] = pd.to_numeric(plays.get('distance'), errors='coerce')
        plays['down'] = pd.to_numeric(plays.get('down'), errors='coerce')

        EXCLUDE_PLAY_TYPES = [
            'Kickoff', 'Kickoff Return (Offense)', 'Kickoff Return Touchdown',
            'Punt', 'Punt Return', 'Punt Return Touchdown',
            'Blocked Punt', 'Blocked Punt Touchdown',
            'Field Goal Good', 'Field Goal Missed', 'Blocked Field Goal',
            'Blocked Field Goal Touchdown', 'Missed Field Goal Return',
            'Missed Field Goal Return Touchdown',
            'Extra Point Good', 'Extra Point Missed', 'Blocked PAT',
            'Two Point Rush', 'Two Point Pass', 'Defensive 2pt Conversion',
            'Timeout', 'Penalty', 'End Period', 'End of Half', 'End of Game',
            'End of Regulation', 'Uncategorized', 'Placeholder',
            'Offensive 1pt Safety', 'Defensive 1pt Safety',
        ]

        PASS_TYPES = ['Pass Reception', 'Pass Incompletion', 'Pass Completion',
                        'Passing Touchdown', 'Sack', 'Interception',
                        'Interception Return', 'Interception Return Touchdown',
                        'Pass Interception Return', 'Pass Interception']
        RUSH_TYPES = ['Rush', 'Rushing Touchdown', 'Fumble Recovery (Own)',
                        'Fumble Recovery (Opponent)']
        THIRD_DOWN_EXCLUDE = [t for t in EXCLUDE_PLAY_TYPES if t != 'Penalty']

        def team_stats(team):
            teamPlays = plays[plays['offense'] == team]
            if teamPlays.empty:
                return (None,) * 10

            scrimmage = teamPlays[~teamPlays['playType'].isin(EXCLUDE_PLAY_TYPES)].copy()
            numPlays = len(scrimmage)

            # PPA per play
            ppaVals = scrimmage['ppa'].dropna()
            ppaPerPlay = ppaVals.mean() if len(ppaVals) else None

            passPlays = scrimmage[scrimmage['playType'].isin(PASS_TYPES)]['ppa'].dropna()
            rushPlays = scrimmage[scrimmage['playType'].isin(RUSH_TYPES)]['ppa'].dropna()
            ppaPass = passPlays.mean() if len(passPlays) else None
            ppaRush = rushPlays.mean() if len(rushPlays) else None

            # Success rate
            successRate = (ppaVals > 0).mean() if len(ppaVals) else None

            # Yards per play
            yards = scrimmage['yardsGained'].sum()
            yardsPerPlay = yards / numPlays if numPlays else None

            # Third down
            thirdPool = teamPlays[~teamPlays['playType'].isin(THIRD_DOWN_EXCLUDE)].copy()
            thirdDowns = thirdPool[thirdPool['down'] == 3].copy()
            thirdDowns = thirdDowns[(thirdDowns['playType'] != 'Penalty') | thirdDowns['playText'].str.contains('1ST DOWN', case=False, na=False)].copy()
            if len(thirdDowns):
                converted = ((thirdDowns['yardsGained'] >= thirdDowns['distance']) | thirdDowns['playText'].str.contains('1ST DOWN', case=False, na=False)).astype(int)
                thirdRate = converted.mean()
            else:
                thirdRate = None

            # Explosives
            explosivesNum = int((scrimmage['ppa'] > 2).sum())
            explosiveRate = explosivesNum / numPlays if numPlays else None

            # Travesties
            travestiesNum = int((scrimmage['ppa'] < -1.5).sum())
            travestiesRate = travestiesNum / numPlays if numPlays else None

            return (ppaPerPlay, ppaPass, ppaRush, successRate, thirdRate, yardsPerPlay,
                    explosivesNum, explosiveRate, travestiesNum, travestiesRate)

        (PPAtotalHome, ppaPassHome, ppaRushHome, SRhomeTotal, thirdDPhome, yardsPerPlayHome,
         explosivesNumHome, explosiveRateHome,
         travestiesNumHome, travestiesRateHome) = team_stats(homeTeam)

        (PPAtotalAway, ppaPassAway, ppaRushAway, SRawayTotal, thirdDaway, yardsPerPlayAway,
         explosivesNumAway, explosiveRateAway,
         travestiesNumAway, travestiesRateAway) = team_stats(awayTeam)

        return (PPAtotalHome, PPAtotalAway, ppaPassHome, ppaPassAway, ppaRushHome, ppaRushAway, SRhomeTotal, SRawayTotal,
                thirdDPhome, thirdDaway, yardsPerPlayHome, yardsPerPlayAway,
                explosivesNumHome, explosivesNumAway,
                explosiveRateHome, explosiveRateAway,
                travestiesNumHome, travestiesNumAway,
                travestiesRateHome, travestiesRateAway)
    
    def liveStatsFromStore(self, game, homeTeam, awayTeam):
        game.poll()
        return self.statisticsToDisplayLive(game.all_plays(), homeTeam, awayTeam)
    def is_live(self, game_info):
        if game_info.get('completed'):
            return False
        start = datetime.fromisoformat(game_info['startDate'])
        return datetime.now(ZoneInfo("America/Chicago")) >= start