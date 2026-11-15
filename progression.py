"""Battle forms derived from species and enhancement, including older units."""

MEGA_SPECIES = {3, 6, 9, 94, 130, 150}
LEGENDARY_TRAITS = {
    144: ('빙하의 군주', '공격 +30% · 필살 +60% · 냉기 4초'),
    145: ('폭풍의 군주', '공격 +30% · 필살 +60% · 게이지 충전 +25%'),
    146: ('불멸의 불꽃', '공격 +30% · 필살 +60% · 화상 7초'),
}


def battle_form(unit):
    dex = unit['dex']
    level = unit.get('enhance', 0)
    threshold = 3 if dex in {144, 145, 146, 150} else 5
    if level < threshold:
        return None
    if dex in MEGA_SPECIES:
        return dict(kind='mega', name='메가 진화', damage=1.35, ultimate=1.6)
    if dex in LEGENDARY_TRAITS:
        name, description = LEGENDARY_TRAITS[dex]
        return dict(kind='legendary', name=name, description=description,
                    damage=1.3, ultimate=1.6)
    return dict(kind='awakened', name='잠재력 각성', damage=1.3, ultimate=1.45)
