"""Move names follow PokeAPI learnsets; combat numbers are this fan game's balance."""
# dex: mode, regular move, ultimate move, visual style
MOVES = {
    1: ('melee', '덩굴채찍', '솔라빔', 'beam'),
    2: ('ranged', '잎날가르기', '솔라빔', 'beam'),
    3: ('ranged', '잎날가르기', '솔라빔', 'beam'),
    4: ('melee', '할퀴기', '화염방사', 'beam'),
    5: ('melee', '베어가르기', '화염방사', 'beam'),
    6: ('ranged', '불꽃세례', '불대문자', 'blast'),
    7: ('melee', '몸통박치기', '하이드로펌프', 'wave'),
    8: ('melee', '물기', '하이드로펌프', 'wave'),
    9: ('ranged', '물대포', '하이드로펌프', 'wave'),
    25: ('ranged', '전기쇼크', '10만볼트', 'storm'),
    26: ('ranged', '전기쇼크', '번개', 'storm'),
    92: ('melee', '핥기', '섀도볼', 'blast'),
    93: ('melee', '핥기', '섀도볼', 'blast'),
    94: ('melee', '섀도펀치', '섀도볼', 'blast'),
    129: ('melee', '몸통박치기', '몸통박치기', 'slash'),
    130: ('melee', '물기', '파괴광선', 'beam'),
    144: ('ranged', '냉동빔', '눈보라', 'storm'),
    145: ('ranged', '전기쇼크', '번개', 'storm'),
    146: ('ranged', '불꽃세례', '불대문자', 'blast'),
    150: ('ranged', '염동력', '사이코키네시스', 'blast'),
    131: ('ranged','냉동빔','눈보라','storm'),
}


def profile(dex):
    mode, move, ultimate, style = MOVES[dex]
    # Short melee lunges reach inner placement sites; projectiles travel two cells.
    attack_range = 1.8 if mode == 'melee' else 2.1
    power, interval = {
        '덩굴채찍':(1,.85), '잎날가르기':(1.1,1.05), '할퀴기':(.75,.65),
        '베어가르기':(1.25,1.15), '불꽃세례':(.85,.8), '몸통박치기':(1.35,1.2),
        '물기':(1.15,.95), '물대포':(.9,.7), '전기쇼크':(.7,.6), '핥기':(.65,.6),
        '섀도펀치':(1.5,1.25), '냉동빔':(1.1,1.1), '염동력':(1.25,1.2),
    }[move]
    ultimate_power = {'솔라빔':4.8,'화염방사':3.4,'불대문자':5,'하이드로펌프':4.2,
                      '10만볼트':3.2,'번개':4.6,'섀도볼':4,'몸통박치기':3,'파괴광선':6,
                      '눈보라':3.8,'사이코키네시스':4.5}[ultimate]
    return {'mode': mode, 'move': move, 'ultimate': ultimate, 'style': style,
            'range': attack_range,
            'ultimateRange': 1.8 if ultimate == '몸통박치기' else 2.1,
            'damageMultiplier': 1.9 if mode == 'melee' else 1,
            'movePower':power, 'ultimatePower':ultimate_power, 'interval':interval}


def skill_set(data):
    """Four automatic attacks with independent reach and recovery."""
    return [
        dict(id='basic', name=data['move'], mode=data['mode'],
             range=data['range'], cooldown=data['interval'], multiplier=1,
             targets=3 if data['mode'] == 'ranged' and data['role'] in ('fire', 'electric', 'psychic') else 1),
        dict(id='close', name='근접 연격', mode='melee', range=1.8,
             cooldown=6, multiplier=2.2, targets=2),
        dict(id='ranged', name='속성 탄환', mode='ranged', range=2.1,
             cooldown=8, multiplier=2.0, targets=3),
        dict(id='ultimate', name=data['ultimate'], mode=data['ultimateMode'],
             range=data['ultimateRange'], cooldown=0, multiplier=1, targets=8),
    ]

