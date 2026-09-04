from datetime import datetime
import streamlit as st
from backend import CFBD
import pandas as pd 
from livegame import LiveGame
import requests

st.set_page_config(page_title="CFB Live Plays", layout="wide")

st.markdown("""
<style>
.element-container.stale-element { opacity: 1 !important; }
[data-testid="stStatusWidget"] { display: none; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_client():
    return CFBD()
@st.cache_resource
def get_game(gid):
    return LiveGame(gid, cfbd=get_client())
def fmt_val(v, pct=False):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.1%}" if pct else f"{v:.2f}"
@st.fragment(run_every=20)
def live_panel(gid, home_team, away_team):
    g = get_game(gid)
    if g.last_error:
        st.warning(g.last_error)
        return


@st.cache_data(ttl=86400)
def get_logos(_client, year):
    teams = _client.pull_teams(year)
    return {
        t["school"]: (t["logos"][0].replace("http://", "https://")
                      if t.get("logos") else None)
        for t in teams
    }
@st.cache_data(ttl=25)
def week_games(_client, year, week, conference):
    return _client.pull_week(year, week, conference)

@st.cache_data(ttl=3600)
def week_plays(_client, year, week):
    return pd.DataFrame(_client.get("/plays", year=year, week=week, classification="fbs"))

@st.cache_data(ttl=3600)
def post_game_stats(_client, game_id, year, week, home, away):
    try:
        box = _client.get("/game/box/advanced", id=game_id)
    except requests.HTTPError:
        return (None,) * 20
    plays = week_plays(_client, year, week)
    playsGame = plays[plays["gameId"] == game_id].copy()
    return _client.statisticsToDisplayPost(box, playsGame, home, away)

def stat_row(label, home_val, away_val, fmt="{:.3f}",
             home_extra=None, away_extra=None):
    def show(v, extra):
        if v is None:
            return "—"
        s = fmt.format(v)
        return f"{s} ({extra})" if extra is not None else s

    a, b, c = st.columns([1, 1, 1])
    a.markdown(f"<div style='text-align:center'>{show(home_val, home_extra)}</div>",
               unsafe_allow_html=True)
    b.markdown(f"<div style='text-align:center; color:gray; font-size:0.85em'>{label}</div>",
               unsafe_allow_html=True)
    c.markdown(f"<div style='text-align:center'>{show(away_val, away_extra)}</div>",
               unsafe_allow_html=True)

@st.fragment(run_every=120)
def week_grid(year_sel, week_sel, conference):
    client = get_client()
    current_week = week_games(client, year_sel, week_sel, conference)
    lines = client.get("/lines", year = year_sel, week = week_sel, classification = 'fbs')
    current_week_lines = {}
    for game in lines:
        line = (game.get('lines') or [{}])[0]
        current_week_lines[game['id']] = {
            'formattedSpread': line.get('formattedSpread'),
            'overUnder': line.get('overUnder'),
        }
        
    for game_id, game in current_week.items():
        game['startDate'] = client.to_central(game['startDate']).isoformat()
    logos = get_logos(client, year_sel)
    games = list(current_week.items())

    for row_start in range(0, len(games), 4):
        cols = st.columns(4)
        for col, (game_id, game_info) in zip(cols, games[row_start:row_start + 4]):
            game_info['formattedSpread'] = current_week_lines.get(game_id, {}).get('formattedSpread', 'N/A')
            game_info['overUnder'] = current_week_lines.get(game_id, {}).get('overUnder', 'N/A')
            with col:
                with st.container(border=True, height=440):
                    home = game_info["homeTeam"]
                    away = game_info["awayTeam"]
                    week = game_info["week"]
                    year = game_info['season']

                    c1, c2, c3, c4 = st.columns([1, 0.5, 1, 3.5])
                    with c1:
                        if logos.get(home):
                            st.image(logos[home], width=50)
                    with c2:
                        st.write("vs")
                    with c3:
                        if logos.get(away):
                            st.image(logos[away], width=50)
                    st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
                    with c4:
                        dt = datetime.fromisoformat(game_info['startDate'].replace('Z', '+00:00'))
                        st.markdown(dt.strftime("%a, %b %-d, %Y: %-I:%M %p CT"))
                        attendance = game_info.get("attendance")
                        if attendance:
                            st.markdown(f'{game_info["venue"]}, {attendance:,} people')
                        else:
                            st.markdown(game_info["venue"])
                        st.markdown(f"Spread: {game_info['formattedSpread']} | O/U: {game_info['overUnder']}")

                    ## printing stats
                    if game_info['completed']:
                        with c1:
                            st.markdown(f"### {game_info['homePoints']}")
                        with c2:
                            st.write("vs")
                        with c3:
                            st.markdown(f"### {game_info['awayPoints']}")
                        PPAtotalHome, PPApassingHome, PPArushingHome, PPAtotalAway, PPApassingAway, PPArushingAway, SRhomeTotal, SRawayTotal, thirdDPhome, thirdDaway, yardsPerPlayHome, yardsPerPlayAway, explosivesNumHome, explosivesNumAway, explosiveRateHome, explosiveRateAway, travestiesNumHome, travestiesNumAway, travestiesRateHome, travestiesRateAway = post_game_stats(client, game_id, year, week, home, away)
                        stat_row("PPA/play", PPAtotalHome, PPAtotalAway)
                        stat_row("PPA/pass", PPApassingHome, PPApassingAway)
                        stat_row("PPA/rush", PPArushingHome, PPArushingAway)
                        stat_row("Success Rate", SRhomeTotal, SRawayTotal,
                                 fmt="{:.0%}")
                        stat_row("Yards/play", yardsPerPlayHome, yardsPerPlayAway,
                                 fmt="{:.2f}")
                        stat_row("3rd down", thirdDPhome, thirdDaway,
                                    fmt="{:.1%}")
                        stat_row("Explosive (>2 PPA)", explosiveRateHome, explosiveRateAway, 
                                    fmt="{:.1%}",
                                    home_extra=explosivesNumHome, away_extra=explosivesNumAway)
                        stat_row("Travesties (<1.5 PPA)", travestiesRateHome, travestiesRateAway,
                                fmt="{:.1%}",
                                home_extra=travestiesNumHome, away_extra=travestiesNumAway)
                    elif game_info.get('completed') is False and client.is_live(game_info):
                        g = get_game(game_id)
                        g.poll()
                        plays_list = g.all_plays()
                        if plays_list:
                            last = plays_list[-1]
                        with c1:
                            st.markdown(f"### {last.get('homeScore')}")
                        with c2:
                            st.write("vs")
                        with c3:
                            st.markdown(f"### {last.get('awayScore')}")
                        st.caption(f"Q{last.get('period')} {last.get('clock')} — {last.get('playText')}")
                        PPAtotalHome, PPAtotalAway, ppaPassHome, ppaPassAway, ppaRushHome, ppaRushAway, SRhomeTotal, SRawayTotal, thirdDPhome, thirdDaway, yardsPerPlayHome, yardsPerPlayAway, explosivesNumHome, explosivesNumAway, explosiveRateHome, explosiveRateAway, travestiesNumHome, travestiesNumAway, travestiesRateHome, travestiesRateAway = CFBD().liveStatsFromStore(g, home, away)
                        stat_row("PPA/play", PPAtotalHome, PPAtotalAway)
                        stat_row("PPA/pass", ppaPassHome, ppaPassAway)
                        stat_row("PPA/rush", ppaRushHome, ppaRushAway)
                        stat_row("Success Rate", SRhomeTotal, SRawayTotal,
                                    fmt="{:.0%}")
                        stat_row("Yards/play", yardsPerPlayHome, yardsPerPlayAway,
                                    fmt="{:.2f}")
                        stat_row("3rd down", thirdDPhome, thirdDaway,
                                    fmt="{:.1%}")
                        stat_row("Explosive (>2 PPA)", explosiveRateHome, explosiveRateAway, 
                                    fmt="{:.1%}",
                                    home_extra=explosivesNumHome, away_extra=explosivesNumAway)
                        stat_row("Travesties (<1.5 PPA)", travestiesRateHome, travestiesRateAway,
                                fmt="{:.1%}",
                                home_extra=travestiesNumHome, away_extra=travestiesNumAway)

class App:
    def __init__(self):
        self.cfbd = get_client()

    def run(self):
        
        st.session_state.setdefault("all_plays", [])
        col1, col2, col3 = st.columns(3)
        yearOptions = list(range(2020, 2027))
        weekOptions = list(range(1, 14))
        conferenceOptions = ['All', 'ACC', 'American', 'Big 12', 'Big Ten', 'CUSA', 'FBS Independents', 'MAC', 'Mountain West', 'Pac-12', 'SEC', 'Sun Belt']

        with col1:
            st.selectbox("Select a year", options=yearOptions, key="year", index = yearOptions.index(2026))
        with col2:
            st.selectbox("Select a week", options=weekOptions, key="week", index = weekOptions.index(self.cfbd.default_week()))
        with col3:
            st.selectbox("Select a conference", options=conferenceOptions, key="conference", index = conferenceOptions.index('All'))
        conferenceChange = {'All': None,
                            'ACC': 'ACC',
                            'American': 'AAC',
                            'Big 12': 'B12',
                            'Big Ten': 'B1G',
                            'CUSA': 'CUSA',
                            'FBS Independents': 'Ind',
                            'MAC': 'MAC',
                            'Mountain West': 'MWC',
                            'Pac-12': 'PAC',
                            'SEC': 'SEC',
                            'Sun Belt': 'SBC'}
        conference = conferenceChange.get(st.session_state.conference)
        week_grid(st.session_state.year, st.session_state.week, conference)

if __name__ == "__main__":
    App().run()
