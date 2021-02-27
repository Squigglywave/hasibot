import pytz
from dotenv import load_dotenv
import os

# Loads environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')      # Bot token
SCHEMA_NAME = os.getenv('ENVIRONMENT')
DB_URL = os.getenv('DATABASE_URL')
PATH = os.getenv('PROJECT_FOLDER')      # Top level project directory

time_zone = pytz.timezone("US/Pacific")

# Echostone values
echostone = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
rates = [1,1,0.9,0.6,0.5775,0.5625,0.5475,0.5325,0.5175,0.5025,0.4875,0.4725,0.4575,0.4425,0.4275,0.4125,0.3975,0.39,0.3825,0.3750,0.3675,0.3600,0.3525,0.3450,0.3375,0.33,0.3225,0.3150,0.3]
boosted_rates = [1, 1, 1.0, 0.7, 0.6775, 0.6625, 0.6475, 0.6325, 0.6174999999999999, 0.6024999999999999, 0.5875, 0.5725, 0.5575, 0.5425, 0.5275, 0.5125, 0.49750000000000005, 0.49, 0.48250000000000004, 0.475, 0.4675, 0.45999999999999996, 0.4525, 0.44499999999999995, 0.4375, 0.43000000000000005, 0.4225, 0.41500000000000004, 0.4]
min_stats = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4,4,4,5,5]
max_stats = [1,1,1,1,1,1,2,2,2,3,3,3,4,4,4,5,5,5,6,6,6,7,7,7,8,8,8,9,9]

# Erg Values
#             5   10  15  20   25   30   35   40    45
erg_rates = [0.9,0.6,0.3,0.15,0.05,0.02,0.01,0.007,0.003]

# lst_scols = ['id', 'name', 'description',
       # 'buy_price', 'tradability', 'icon',
       # 'width', 'height', 'stack',
       # 'item_type', 'weapon_type', 'attack_speed', 'down_hit_count', 'range',
       # 'min_damage', 'max_damage', 'min_injury', 'max_injury', 'critical',
       # 'balance', 'defense', 'protection', 'durability', 'upgrade_count',
       # 'gem_upgrade_count', 'can_reforge', 'has_enchants', 'has_upgrades',
       # 'has_gem_upgrades', 'intro_revision', 'set_effects']
       
lst_scols = ['name','xml_string','min_damage', 'max_damage', 'critical',
       'balance', 'defense', 'protection', 'durability', 'set_effects']
