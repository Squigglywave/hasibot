import random
from config import min_stats,max_stats,rates,echostone

def roll_supplement(grade):
    min_stat = min_stats[grade]
    max_stat = max_stats[grade]
    roll = random.randint(min_stat,max_stat)

    return roll

def get_echo_30():
    total_stat = 1
    grade = 1
    attempts = 0
    stat_gains = []
    
    while grade < 29:
        roll = random.random()
        success = roll < rates[grade-1]
        stat_roll = roll_supplement(grade)
        if success:
            grade = grade + 1
            total_stat = total_stat + stat_roll
            if grade > 24:
                stat_gains.append(stat_roll)
        elif grade > 24:
            grade = grade - 1
            total_stat = total_stat - stat_gains.pop()
        attempts = attempts + 1
        
    return attempts, total_stat