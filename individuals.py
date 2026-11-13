"""Defense-relevant IVs, merged by independent per-stat maxima."""
import random

def roll_ivs():
    return {key:random.randint(0,31) for key in ('attack','special','speed')}

def iv_factor(unit,key):
    value=unit.get('ivs',{}).get(key)
    return 1 if value is None else .9 + .2*value/31

def attack_interval(unit,catalog):
    value=unit.get('ivs',{}).get('speed',0)
    return catalog[unit['dex']]['interval']*(1-.12*value/31)

def iv_grade(unit):
    total=sum(unit.get('ivs',{}).values())
    return 'S' if total>=84 else 'A' if total>=70 else 'B' if total>=50 else 'C' if total>=30 else 'D'

