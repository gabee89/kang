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
}


def profile(dex):
    mode, move, ultimate, style = MOVES[dex]
    return {'mode': mode, 'move': move, 'ultimate': ultimate, 'style': style,
            'range': 2.15 if mode == 'melee' else 4.4,
            'damageMultiplier': 1.9 if mode == 'melee' else 1,
            'interval': 1.05 if mode == 'melee' else .9}

