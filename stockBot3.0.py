import yfinance as yf
from discord.ext import commands
import datetime
import pytz
import holidays
import asyncio
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time
import pickle
import os

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId

app = IBapi()

def run_loop():
    app.run()

# Function to create FX Order contract
def makeContract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'STK'
    contract.exchange = 'SMART'
    contract.currency = 'USD'
    contract.primaryExchange = 'NASDAQ'
    return contract

def makeTrade(symbol, quantity, action):
    app.connect('127.0.0.1', 7497, 123)

    app.nextorderId = None

    # Start the socket in a thread
    api_thread = threading.Thread(target=run_loop, daemon=True)
    api_thread.start()

    # Check if the API is connected via orderid
    while True:
        if isinstance(app.nextorderId, int):
            print('connected')
            break
        else:
            print('waiting for connection')
            time.sleep(1)

    # Create order object
    order = Order()
    order.action = action
    order.totalQuantity = quantity
    order.orderType = 'MKT'

    # Place order
    app.placeOrder(app.nextorderId, makeContract(symbol), order)
    app.nextorderId += 1
    time.sleep(3)
    app.disconnect()

tz = pytz.timezone('US/Eastern')
us_holidays = holidays.US()
def afterHours(now = None):
    if not now:
        now = datetime.datetime.now(tz)

    openTime = datetime.time(hour = 9, minute = 30, second = 0)
    closeTime = datetime.time(hour = 16, minute = 0, second = 0)

    # If a holiday
    if now.strftime('%Y-%m-%d') in us_holidays:
        return True

    # If before 0930 or after 1600
    if (now.time() < openTime) or (now.time() > closeTime):
        return True

    # If it's a weekend
    if now.date().weekday() > 4:
        return True

    return False

client = commands.Bot(command_prefix='!')

class Stock:
    def __init__(self, symbol, usd):
        self.symbol = symbol
        self.alreadyHave = False
        self.data = []
        self.amountBought = 0
        self.priceBoughtAt = 0
        self.previousPrices = []
        self.shares = 0
        self.isUSD = usd

#Constraints
money = 4895
limit = 0.1
investmentLossMargin = 0.05
investmentProfitMargin = 0.05

#In seconds(60)
refreshRate = 60

#How much data points you want(400)
dataPoints = 400
lastQuarter = int(dataPoints / 4) * 3
lastFortieth = int(dataPoints / 40) * 39

#Collection of stocks
stocks = [Stock('NFLX', True), Stock('DIS', True), Stock('MSFT', True),
          Stock('DIS', True), Stock('TSLA', True), Stock('AMD', True),
          Stock('NVDA', True), Stock('INTC', True), Stock('SHOP', True),
          Stock('SNE', True), Stock('GOOG', True), Stock('AAPL', True),
          Stock('BB', True), Stock('AMZN', True), Stock('FB', True)]

try:
    with open("stocks.txt", "rb") as filehandler:
        stocks = pickle.load(filehandler)
        money = pickle.load(filehandler)
        for stock in stocks:
            while len(stock.data) > dataPoints:
                stock.data.pop(0)
                stock.previousPrices.pop(0)

except:
    with open("stocks.txt", "wb") as filehandler:
        pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
        pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

#Less accurate as time increases
timeToCollectData = (dataPoints - len(stocks[len(stocks) - 1].data)) * refreshRate / 60

@client.event
async def on_ready():
    try:
        generalChannel = client.get_channel(805608327538278423)
        await generalChannel.send("-----------------StockBot is Online!-----------------")
        await generalChannel.send("Collecting Data (" + str(round(timeToCollectData, 2)) + " mins)...")
        while True:
            for i in stocks:
                if afterHours() == True:
                    await generalChannel.send("After hours")
                    await asyncio.sleep(1800)
                    break

                currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]
                if i.isUSD == True:
                    currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                if len(i.data) >= dataPoints:
                    i.data.pop(0)
                    i.previousPrices.pop(0)
                    i.previousPrices.append(currentPrice)
                    percentChange = (currentPrice - i.previousPrices[-1]) / i.previousPrices[-1]
                    i.data.append(percentChange)

                else:
                    i.previousPrices.append(currentPrice)
                    percentChange = (currentPrice - i.previousPrices[-1]) / i.previousPrices[-1]
                    i.data.append(percentChange)

                os.remove("stocks.txt")
                with open("stocks.txt", "wb") as filehandler:
                    pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
                    pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

            if len(stocks[len(stocks) - 1].data) == dataPoints:
                await generalChannel.send("Done Collecting Data")
                await generalChannel.send("Starting Trades...")
                break

            await asyncio.sleep(refreshRate)

        await trade()

    except Exception as e:
        print("On Ready: " + str(e))
        await asyncio.sleep(refreshRate)
        await on_ready()

async def trade():
    while True:
        try:
            generalChannel = client.get_channel(805608327538278423)
            global money
            for i in stocks:
                if afterHours() == True:
                    await generalChannel.send("After hours")
                    await asyncio.sleep(1800)
                    break

                currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]
                moneyMade = 0

                if i.isUSD == True:
                    currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                percentChange = (currentPrice - i.previousPrices[-1]) / i.previousPrices[-1]

                if i.alreadyHave == True:
                    priceChange = (currentPrice - i.priceBoughtAt) / i.priceBoughtAt * i.amountBought
                    currentValue = i.amountBought + priceChange
                    moneyMade = priceChange - min(max(i.shares * 0.01, 1), currentValue * 0.5) - min(max(i.shares * 0.01, 1), i.amountBought * 0.5)

                if len(i.data) >= dataPoints:
                    i.data.pop(0)
                    i.data.append(percentChange)
                    i.previousPrices.pop(0)
                    i.previousPrices.append(currentPrice)

                os.remove("stocks.txt")
                with open("stocks.txt", "wb") as filehandler:
                    pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
                    pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

                average = 0
                averageLastQuarter = 0
                averageLastFortieth = 0
                priceAverage = 0
                shares = 0
                highest = 0

                for j in range(dataPoints):
                    average = average + i.data[j]
                    priceAverage = priceAverage + i.previousPrices[j]
                    if j > lastQuarter:
                        averageLastQuarter = averageLastQuarter + i.data[j]

                    if j > lastFortieth:
                        averageLastFortieth = averageLastFortieth + i.data[j]

                    if i.previousPrices[j] > highest:
                        highest = i.previousPrices[j]

                spending = money * limit
                if spending > currentPrice:
                    while spending > currentPrice:
                        spending = spending - currentPrice
                        shares = shares + 1

                average = average / dataPoints
                averageLastQuarter = averageLastQuarter / (dataPoints / 4)
                averageLastFortieth = averageLastFortieth / (dataPoints / 40)
                priceAverage = priceAverage / dataPoints
                amountBought = shares * currentPrice
                change = (priceAverage - currentPrice) / currentPrice * amountBought
                potentialMoneyMade = change - min(max(shares * 0.01, 1), amountBought * 0.5) - min(max(shares * 0.01, 1), (amountBought + change) * 0.5)

                if ((average > 0 and potentialMoneyMade > 0) or (average > 0 and averageLastQuarter < 0 and averageLastFortieth > 0)) and i.alreadyHave == False:
                    spending = money * limit
                    if spending > currentPrice:
                        while spending > currentPrice:
                            spending = spending - currentPrice
                            i.shares = i.shares + 1

                        try:
                            #Buy stock
                            makeTrade(i.symbol, i.shares, 'BUY')
                            i.alreadyHave = True
                            i.priceBoughtAt = currentPrice
                            i.amountBought = i.shares * i.priceBoughtAt
                            money = money - i.amountBought
                            await generalChannel.send('Buying $' + str(round(i.amountBought, 2)) + ' of ' + i.symbol)
                            await generalChannel.send('Number of Shares: ' + str(i.shares))

                        except Exception as e:
                            print("Buying: " + str(e))
                            await generalChannel.send('Damn that sucks, servers are down but ' + i.symbol + ' is a good buy rn!')

                elif i.alreadyHave == True and (moneyMade > i.amountBought * investmentProfitMargin or moneyMade < i.amountBought * investmentLossMargin * -1 or (moneyMade > 1 and percentChange > 1)):
                    try:
                        #Sell stock
                        makeTrade(i.symbol, i.shares, 'SELL')
                        i.shares = 0
                        i.alreadyHave = False
                        money = money + moneyMade + i.amountBought
                        i.amountBought = 0
                        await generalChannel.send('Selling of all of ' + i.symbol)
                        await generalChannel.send('Money made = ' + str(round(moneyMade, 2)))

                    except Exception as e:
                        print("Selling: " + str(e))
                        await generalChannel.send('Bruh, I can\'t sell ' + i.symbol + ' right now!')

            await asyncio.sleep(refreshRate)

        except Exception as e:
            print("Trade: " + str(e))
            await asyncio.sleep(refreshRate)

@client.command(name='sell')
async def sell(context, arg1):
    try:
        for i in stocks:
            if i.symbol == arg1:
                if i.alreadyHave == True:
                    currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                    if i.isUSD == True:
                        currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                    priceChange = (currentPrice - i.priceBoughtAt) / i.priceBoughtAt * i.amountBought
                    currentValue = i.amountBought + priceChange
                    moneyMade = priceChange - min(max(i.shares * 0.01, 1), currentValue * 0.5) - min(max(i.shares * 0.01, 1), i.amountBought * 0.5)
                    await context.message.channel.send('Money Made if ' + i.symbol + ' was sold: $' + str(round(moneyMade, 2)))

                else:
                    await context.message.channel.send('You don\'t have any of this stock!')

                break

    except Exception as e:
        print("Sell: " + str(e))

@client.command(name='portfolio')
async def portfolio(context):
    try:
        global money
        sum = money
        await context.message.channel.send('You have $' + str(round(money, 2)) + ' to spend!')
        for i in stocks:
            sum = sum + i.amountBought

        await context.message.channel.send('Portfolio Contains: $' + str(round(sum, 2)))

    except Exception as e:
        print("Portfolio: " + str(e))

@client.command(name='status')
async def status(context):
    try:
        await context.message.channel.send('If nothing shows up you don\'t have any stocks currently')
        for i in stocks:
            currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]
            if i.isUSD == True:
                currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

            if i.alreadyHave == True:
                priceChange = ((currentPrice - i.priceBoughtAt) / i.priceBoughtAt) * 100
                await context.message.channel.send(i.symbol + ': $' + str(round(i.amountBought, 2)) + ' ------- priceChange = ' + str(round(priceChange, 2)))

            if (money * limit) < currentPrice:
                await context.message.channel.send('Spending limit too low to buy more of ' + i.symbol)

    except Exception as e:
        print("Status: " + str(e))

@client.command(name='info')
async def info(context, arg1):
    try:
        for i in stocks:
            if i.symbol == arg1:
                await context.message.channel.send('-------' + i.symbol + '-------')
                if len(i.data) < dataPoints:
                    await context.message.channel.send('Still Processing...')
                    break

                average = 0
                averageLastQuarter = 0
                averageLastFortieth = 0
                priceAverage = 0
                currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                if i.isUSD == True:
                    currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                for j in range(dataPoints):
                    average = average + i.data[j]
                    priceAverage = priceAverage + i.previousPrices[j]
                    if j > lastQuarter:
                        averageLastQuarter = averageLastQuarter + i.data[j]

                    if j > lastFortieth:
                        averageLastFortieth = averageLastFortieth + i.data[j]

                spending = money * limit
                shares = 0
                if spending > currentPrice:
                    while spending > currentPrice:
                        spending = spending - currentPrice
                        shares = shares + 1

                average = average / dataPoints
                averageLastQuarter = averageLastQuarter / (dataPoints / 4)
                averageLastFortieth = averageLastFortieth / (dataPoints / 40)
                priceAverage = priceAverage / dataPoints
                potentialMoneyMade = (priceAverage - currentPrice) / currentPrice * (shares * currentPrice) - min(max(shares * 0.01, 1), priceAverage * 0.5) - min(max(shares * 0.01, 1), currentPrice * 0.5)
                await context.message.channel.send('Average: ' + str(average))
                await context.message.channel.send('Last Quarter Average: ' + str(averageLastQuarter))
                await context.message.channel.send('Last Fortieth Average: ' + str(averageLastFortieth))
                await context.message.channel.send('Potential Money Made if Bought Now: $' + str(round(potentialMoneyMade, 2)))
                break

    except Exception as e:
        print("Info: " + str(e))

#Run the client on the server
client.run('ODA1NjEzMTczMzYwODIwMjc3.YBdbvA.M8upIcRfyRpDibiu9j81ic8mbC4')