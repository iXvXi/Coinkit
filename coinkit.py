import os
import time
import sys
import requests
import subprocess
from termcolor import cprint
from pyfiglet import figlet_format
from decimal import Decimal
from operator import itemgetter
import asyncio
import json
import random

s = requests.session()
loop = asyncio.get_event_loop()


def ccbanner():
    os.system('cls' if os.name == 'nt' else 'clear')
    cprint("""        
 :'######:::'#######::'####:'##::: ##::::'##:::'##:'####:'########:
 '##... ##:'##.... ##:. ##:: ###:: ##:::: ##::'##::. ##::... ##..::
  ##:::..:: ##:::: ##:: ##:: ####: ##:::: ##:'##:::: ##::::: ##::::
  ##::::::: ##:::: ##:: ##:: ## ## ##:::: #####::::: ##::::: ##::::
  ##::::::: ##:::: ##:: ##:: ##. ####:::: ##. ##:::: ##::::: ##::::
  ##::: ##: ##:::: ##:: ##:: ##:. ###:::: ##:. ##::: ##::::: ##::::
 . ######::. #######::'####: ##::. ##:::: ##::. ##:'####:::: ##::::
 :......::::.......:::....::..::::..:::::..::::..::....:::::..:::::      
    """, 'yellow')


def menu():
    global loop
    cprint('    =========================================================', 'yellow')
    cprint('         ==================== MENU =====================', 'cyan')
    cprint('              1. Pump Watch         2. Commission Calc.    ', 'yellow')
    print('\n')
    option = input("Select an option: ")
    selection = ['1', '2', '3', '4', '5']
    for selection in option:
        try:
            if selection == '1':
                banner()
                cprint('                 LOADING COINS', 'cyan')
                task = loop.create_task(price())
                task1 = loop.create_task(stats())

                loop.run_until_complete(asyncio.gather(task, task1))
                loop.close()
            elif selection == '2':
                calc()
                mainmenu()

        except (KeyboardInterrupt, SystemExit):
            mainmenu()
            raise


def mainmenu():  # Main menu
    mm = input(" Would You Like To Return To The Main Menu? ")
    if mm == "yes" or mm == "y":
        ccbanner()
        menu()
    else:
        sys.exit()


def banner():  # Banner
    os.system('cls' if os.name == 'nt' else 'clear')
    cprint("""
 ____                         __        __    _       _     
|  _ \ _   _ _ __ ___  _ __   \ \      / /_ _| |_ ___| |__  
| |_) | | | | '_ ` _ \| '_ \   \ \ /\ / / _` | __/ __| '_ \ 
|  __/| |_| | | | | | | |_) |   \ V  V / (_| | || (__| | | |
|_|    \__,_|_| |_| |_| .__/     \_/\_/ \__,_|\__\___|_| |_|
                      |_|                                       
       """, 'cyan')
    time.sleep(2)


coin_name_list = [
    "BTC",
    "NAV",
    "SNM",
    "BTG",
    "ZCL",
    "GNT",
    "ETH",
    "BCH",
    "CLOAK",
    "DASH",
    "LSK",
    "KMD",
    "SC",
    "STEEM",
    "TRX",
    "XMR",
    "ZEC",
    "LTC"
]


coin_list = []

class Measurement:
    def __init__(self, name):
        self.name = name
        self.values = []
        self.change = 0
        self.diff = 0

    def add_measurement(self, val):
        if len(self.values) == 0:
            self.values.append(val)

        if self.values[0] == val:
            return
        self.values.append(val)

    def calc_change(self):
        if len(self.values) < 2:
            return 0

        previous = self.values[0]
        latest = self.values[1]

        self.change = 0

        self.increase = True
        if latest > previous:
            self.diff = Decimal(latest) - Decimal(previous)
        else:
            self.diff = Decimal(previous) - Decimal(latest)
            self.increase = False

        self.change = percentchange(previous, latest)
        self.values.pop(0)
        return self.change

    def display_change(self):

        if self.change == 0:
            return

        color = None
        label = None
        if self.increase:
            color = 'green'
            label = "(+)Increase"
        else:
            color = 'red'
            label = '(-)Decrease'

        cprint(("\t{}: {} of: {:.7f} {:.4f}% Change".format(self.name, label, self.diff, self.change)), color)


class CoinStat:

    def __init__(self, label, name, members=[], measurement_name=None):

        self.label = label
        self.json_name = name
        self.json_member_dict = {}
        self.json_measurement_dict = {}
        self.measurement_name = measurement_name
        self.members = members

        for json_member in members:
            self.json_member_dict[json_member] = 0

        if measurement_name:
            self.json_measurement_dict[measurement_name] = Measurement(measurement_name)

    def update(self, data):

        fudge = 0 #random.randint(-1,1)
        rdata = data[self.json_name]
        for json_name, dummy in self.json_member_dict.items():

            try:
                self.json_member_dict[json_name] = rdata[json_name]
            except KeyError:
                #print(json_name, json.dumps(rdata, indent=2))
                pass

        for json_name, dummy in self.json_measurement_dict.items():
            measurement = self.json_measurement_dict[json_name]
            try:
                val = rdata[json_name] + fudge
                measurement.add_measurement(val)
                measurement.calc_change()

            except KeyError:
                #print(json_name, json.dumps(rdata, indent=2))
                pass


    def display(self):

        color = 'cyan'
        measurement = None
        measurement_val = 0
        if self.measurement_name:
            for json_name, dummy in self.json_measurement_dict.items():
                measurement = self.json_measurement_dict[json_name]
                if len(measurement.values):
                    measurement_val = measurement.values[0]
                if measurement.change:
                    if measurement.increase:
                        color = 'green'
                    else:
                        color = 'red'

        string = self.label + ": "
        if measurement:
            string += " {}, {}".format(measurement.name, measurement_val)

        for member in self.members:
            string += ", {}, {}".format(member, self.json_member_dict[member])

        cprint(("\t{}".format(string)), color)


class Coin:

    dict = {}

    def __init__(self, name, id):

        if not Coin.lookup(name):
            self.name = name
            self.id = id
            self.change = 0
            self.stats = None
            self.dict[name] = self
            self.usd = 0
            self.btc = 0

            self.price_measurement = Measurement("Price")
            self.stat_measurements = {}

            self.stat_measurements['twitter'] = CoinStat('Twitter', 'Twitter', ['followers', 'statuses'], 'Points')
            self.stat_measurements['reddit'] = CoinStat('Reddit', 'Reddit', ['active_users', 'posts_per_hour', 'comments_per_hour', 'Points'], 'subscribers')
            self.stat_measurements['facebook'] = CoinStat('Facebook', 'Facebook', ['links', 'talking_about'], 'Points')



    @staticmethod
    def lookup(name):
        if name in Coin.dict:
            return Coin.dict[name]
        else:
            return None

    def add_price(self, latest_price, display = True):

        self.price_measurement.add_measurement(latest_price)
        self.change = self.price_measurement.calc_change()
        if display:
            self.price_measurement.display_change()
        return

    def update_stats(self, data):

        for name, stat in self.stat_measurements.items():
            stat.update(data)
        return

    def display_stats(self):

        for name, stat in self.stat_measurements.items():
            stat.display()
        return


async def price():
    while True:
        await price_core(False)
        await asyncio.sleep(5)


async def stats():

    while True:
        for coin in coin_list:
            # https://www.cryptocompare.com/api/data/socialstats/?id=1182
            data = await call_api2('https://www.cryptocompare.com/api/data/socialstats/?id={}'.format(coin.id))
            coin.stats = data['Data']
            coin.update_stats(coin.stats)

        await asyncio.sleep(10)



def call_api(str=None, delay_on_error=20):
    try:
        api = str
        raw = requests.get(api)
        return raw.json()
    except requests.exceptions.ConnectionError:
        time.sleep(delay_on_error)
        return None

async def call_api2(str=None, delay_on_error=20):
    try:
        api = str
        raw = requests.get(api)
        return raw.json()
    except requests.exceptions.ConnectionError:
        time.sleep(delay_on_error)
        return None

def init():
    data = call_api('https://min-api.cryptocompare.com/data/all/coinlist')
    for coin_name in coin_name_list:
        coin_list.append(Coin(coin_name,data['Data'][coin_name]['Id']))


async def price_core(display = True):
    # cprint(datetime.datetime.now(), 'blue', attrs=['blink'])

    for coin_name in coin_name_list:

        if display:
            cprint('===================== {} ======================'.format(coin_name), 'yellow')

        # try:
        #    raw = requests.get('https://min-api.cryptocompare.com/data/price?fsym={}&tsyms=BTC,USD'.format(coin_name))
        # except requests.exceptions.ConnectionError:
        #    await asyncio.sleep(20)
        #    return
        data = await call_api2('https://min-api.cryptocompare.com/data/price?fsym={}&tsyms=BTC,USD'.format(coin_name))

        coin = Coin.lookup(coin_name)

        coin.usd = data['USD']
        coin.btc = data['BTC']

        if coin_name == "BTC":
            hist_url = "https://min-api.cryptocompare.com/data/histominute?fsym={}&tsym=BTC&limit=1&aggregate=0&e=CCCAGG".format("BTC")
        else:
            hist_url = "https://min-api.cryptocompare.com/data/histominute?fsym={}&tsym=BTC&limit=1&aggregate=0&e=CCCAGG".format(coin_name)

        await gethistoryprice(coin, hist_url, display)

    #newlist = coin_list.sort(key=itemgetter('change'), reverse=True)

    print('\n')
    cprint('===================== PRICE ======================', 'cyan')
    cprint('{0: <10}  {1: <15}  {2: <15} {3: <15}'.format('Name', 'USD', 'BTC', 'Change'), 'cyan')

    for coin in coin_list:
        cprint('{0: <10} {1: <15.08f} {2: <15.08f} {3: <15}'.format(
            coin.name,
            coin.usd,
            coin.btc,
            coin.change), 'cyan')

        coin.price_measurement.display_change()
        coin.display_stats()

    print('\n')


# Gets the percentage changed between two prices, returns ints

def percentchange(previous, current):
    if previous == current or previous == 0 or current == 0:
        return 0
    else:
        return ((current - previous) / previous) * 100


async def gethistoryprice(coin, url, display=True):
    while True:

        minutechart = await call_api2(url)

        if not minutechart or not minutechart['Data']:
            return

        # list indexing from multiple nested lists/dicts

        try:
            a = minutechart['Data'][-1]['close']
        except IndexError:
            print(minutechart)
            os._exists(1)

        coin.add_price(a, display)

        return


def calc():
    print("\n")
    cprint("Exchange Commission Calculator", "yellow")
    cprint("Commission Percentage", "cyan")
    cprint("""
    Binance w/o bnb= 0.50%
    Bitttrex= 0.25%""", "cyan")
    cc = float(input("Enter Commission Percentage: "))
    print("\n")
    ftp = float(input("Enter First Trade Position In BTC: "))
    stp = float(input("Enter Second Trade Position In BTC: "))
    profit = stp - ftp
    total = stp + profit  # math wrong af
    print("Your Final BTC total is "), (total)


init()
ccbanner()
menu()
