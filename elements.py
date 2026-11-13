"""Gen-I elemental matchups; multiply both defending types, including immunities."""
TYPES = {19:('normal',),41:('poison','flying'),46:('bug','grass'),74:('rock','ground'),
         23:('poison',),48:('bug','poison'),66:('fighting',),111:('ground','rock'),
         52:('normal',),95:('rock','ground'),149:('dragon','flying')}
CHART = {
    'fire': {'grass':2,'ice':2,'bug':2,'fire':.5,'water':.5,'rock':.5,'dragon':.5},
    'water': {'fire':2,'ground':2,'rock':2,'water':.5,'grass':.5,'dragon':.5},
    'grass': {'water':2,'ground':2,'rock':2,'fire':.5,'grass':.5,'poison':.5,'flying':.5,'bug':.5,'dragon':.5},
    'electric': {'water':2,'flying':2,'electric':.5,'grass':.5,'dragon':.5,'ground':0},
    'ice': {'grass':2,'ground':2,'flying':2,'dragon':2,'water':.5,'ice':.5},
    'ghost': {'ghost':2,'psychic':0,'normal':0},
    'psychic': {'poison':2,'fighting':2,'psychic':.5},
}
NAMES={'normal':'노말','fire':'불꽃','water':'물','grass':'풀','electric':'전기','ice':'얼음',
       'poison':'독','flying':'비행','bug':'벌레','ground':'땅','rock':'바위','fighting':'격투','dragon':'드래곤','ghost':'고스트','psychic':'에스퍼'}
def effectiveness(role, types):
    value=1
    for kind in types:
        value*=CHART.get(role,{}).get(kind,1)
    return value

