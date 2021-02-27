from config import erg_rates
import random


def roll_erg(rank):
    roll = random.random()
    success = roll < erg_rates[rank]

    return success
        
