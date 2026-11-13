"""One server-owned encounter and weather roll per round, previewed in preparation."""
import random
from elements import TYPES, effectiveness

ENEMIES = {19:'꼬렛', 41:'주뱃', 46:'파라스', 74:'꼬마돌',
           23:'아보', 48:'콘팡', 66:'알통몬', 111:'뿔카노'}
WEATHER = {
    'clear': ('맑음', '속성 보정 없음', {}),
    'rain': ('비', '물 +20% · 전기 +15% · 불 -15%', {'water':1.2,'electric':1.15,'fire':.85}),
    'heat': ('폭염', '불 +20% · 풀 +10% · 얼음 -15%', {'fire':1.2,'grass':1.1,'ice':.85}),
    'snow': ('눈', '얼음 +20% · 물 +10% · 불 -10%', {'ice':1.2,'water':1.1,'fire':.9}),
    'wind': ('바람', '풀 +15% · 전기 +10%', {'grass':1.15,'electric':1.1}),
}
THEMES = (('forest','햇살 숲'), ('valley','안개 계곡'), ('volcano','불씨 협곡'),
          ('snowfield','눈꽃 설원'), ('moonlit','달빛 유적'))


def make_plan(number):
    dex = random.choice(tuple(ENEMIES))
    weather = random.choice(tuple(WEATHER))
    name, hint, _ = WEATHER[weather]
    theme, theme_name = THEMES[min(4, max(0, (number-1)//10))]
    boss = number % 10 == 0
    shortcut = number % 4 == 0 and not boss
    direction = -1 if random.getrandbits(1) else 1
    plan = {'round':number, 'dex':149 if boss else dex,
            'name':'공동 보스 망나뇽' if boss else ENEMIES[dex],
            'types':['dragon','flying'] if boss else list(TYPES[dex]),
            'weather':weather, 'weatherName':name, 'weatherHint':hint,
            'theme':theme, 'themeName':theme_name,
            'entry':'shortcut' if shortcut else 'main',
            'direction':direction, 'directionName':'역방향' if direction==-1 else '정방향',
            'entryName':'샛길 개방 · 중간 포털 진입' if shortcut else '기본 포털 진입'}
    plan['matchups']={role:round(effectiveness(role,plan['types'])*WEATHER[weather][2].get(role,1),2)
                      for role in ('grass','fire','water','electric','ice','ghost','psychic')}
    return plan


def damage_bonuses(plan):
    return WEATHER.get((plan or {}).get('weather'), WEATHER['clear'])[2]

