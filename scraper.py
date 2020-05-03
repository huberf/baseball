import requests as r
from bs4 import BeautifulSoup
import json
import re

data_url = 'https://www.baseball-reference.com/leagues/MLB/2019-schedule.shtml'

print('Starting scrape...')
data = r.get(data_url)
soup = BeautifulSoup(data.text, features="html.parser")
sections = soup.findAll('div', { 'class': ['section_wrapper'] })
# drop bottom navigation
sections = sections[:-1]
sections = [soup.find('div', { 'id': 'div_4541204352' }), \
            soup.find('div', { 'id': 'div_7506607405' })]
all_data = []
for sect in sections:
    #print(list(contents.children))
    for i in list(sect.children)[1:]:
        str_i = str(i)
        if str_i == '\n':
            continue
        try:
            date = re.search("<h3>(.*)</h3>", str_i)[1]
        except TypeError:
            print('TypeError on date:', str_i[0] == '\n')
        for game in BeautifulSoup(str_i, features="html.parser").findAll('p', { 'class': ['game'] }):
            first_found = False
            team_a = ''
            team_b = ''
            score_a = -1
            score_b = -1
            win_a = False
            for ch in game.children:
                score = re.search('[(]([0-9]*)[)]', str(ch))
                if not score == None:
                    if first_found:
                        score_b = score[1]
                    else:
                        score_a = score[1]
                name = re.search('">(.*)</a>', str(ch))
                strong = re.search('strong', str(ch))
                if not strong == None:
                    if first_found:
                        win_a = False
                    else:
                        win_a = True
                if not name == None:
                    if first_found:
                        if team_b == '':
                            team_b = name[1]
                    else:
                        first_found = True
                        team_a = name[1]
            all_data.append({
                'home_team': team_b,
                'away_team': team_a,
                'score_home': score_b,
                'score_away': score_a,
                'winning_team': team_a if win_a else team_b,
                'location': team_b,
                'month': date.split(' ')[1],
                'day': date.split(' ')[2][:-1],
                'year': date.split(' ')[3],
                'week_day': date.split(' ')[0][:-1]
                })
open('baseball_data.json', 'w').write(json.dumps(all_data, indent=2))
print('Done.')
