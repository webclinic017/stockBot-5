import yfinance as yf
from discord.ext import commands
import datetime
import asyncio
import pickle
import os

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
money = 5000
limit = 0.2
investmentLossMargin = 0.05

#In seconds(30)
refreshRate = 60

#How much data points you want(100)
dataPoints = 200
lastQuarter = int(dataPoints / 4) * 3
lastSixteenth = int(dataPoints / 16) * 15

#Collection of stocks
stocks = [Stock('BTC-USD', True), Stock('ETH-USD', True), Stock('DOGE-USD', True),
          Stock('XRP-USD', True), Stock('HNT1-USD', True), Stock('LTC-USD', True)]

try:
    with open("crypto.txt", "rb") as filehandler:
        stocks = pickle.load(filehandler)
        money = pickle.load(filehandler)
        for stock in stocks:
            while len(stock.data) > dataPoints:
                stock.data.pop(0)
                stock.previousPrices.pop(0)
except:
    with open("crypto.txt", "wb") as filehandler:
        pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
        pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

#Less accurate as time increases
timeToCollectData = (dataPoints - len(stocks[len(stocks) - 1].data)) * refreshRate / 60

@client.event
async def on_ready():

    try:
        generalChannel = client.get_channel(805608327538278423)
        await generalChannel.send("-----------------CyrptoBot is Online!-----------------")
        await generalChannel.send("Collecting Data (" + str(round(timeToCollectData, 2)) + " mins)...")
        while True:

            for i in stocks:
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

                os.remove("crypto.txt")
                with open("crypto.txt", "wb") as filehandler:
                    pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
                    pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

            if len(stocks[len(stocks) - 1].data) >= dataPoints:
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

                    currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]
                    moneyMade = 0

                    if i.isUSD == True:
                        currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                    if i.alreadyHave == True:
                        change = (currentPrice - i.priceBoughtAt) / i.priceBoughtAt * i.amountBought
                        currentValue = i.amountBought + change
                        moneyMade = change - (i.amountBought * 0.015) - (currentValue * 0.015)

                    percentChange = (currentPrice - i.previousPrices[-1]) / i.previousPrices[-1]

                    if len(i.data) >= dataPoints:
                        i.data.pop(0)
                        i.previousPrices.pop(0)
                        i.data.append(percentChange)
                        i.previousPrices.append(currentPrice)

                    os.remove("crypto.txt")
                    with open("crypto.txt", "wb") as filehandler:
                        pickle.dump(stocks, filehandler, pickle.HIGHEST_PROTOCOL)
                        pickle.dump(money, filehandler, pickle.HIGHEST_PROTOCOL)

                    average = 0
                    averageLastQuarter = 0
                    averageLastSixteenth = 0
                    priceAverage = 0

                    for j in range(dataPoints):
                        average = average + i.data[j]
                        priceAverage = priceAverage + i.previousPrices[j]

                        if j > lastQuarter:
                            averageLastQuarter = averageLastQuarter + i.data[j]

                        if j > lastSixteenth:
                            averageLastSixteenth = averageLastSixteenth + i.data[j]

                    spending = money * limit
                    average = average / dataPoints
                    averageLastQuarter = averageLastQuarter / (dataPoints / 4)
                    averageLastSixteenth = averageLastSixteenth / (dataPoints / 16)
                    priceAverage = priceAverage / dataPoints
                    change = (priceAverage - currentPrice) / currentPrice * spending
                    potentialMoneyMade = change - (spending * 0.015) - (spending + change) * 0.015
                    i.shares = 0

                    if ((average > 0 and potentialMoneyMade > 0) or (averageLastQuarter < 0 and averageLastSixteenth > 0)) and i.alreadyHave == False:
                        spending = money * limit
                        #Buy stock
                        i.alreadyHave = True
                        i.priceBoughtAt = currentPrice
                        i.amountBought = spending
                        money = money - i.amountBought
                        await generalChannel.send('Buying $' + str(round(i.amountBought, 2)) + ' of ' + i.symbol)

                    elif i.alreadyHave == True and (moneyMade > 0 or moneyMade < i.amountBought * investmentLossMargin * -1):
                        #Sell stock
                        i.shares = 0
                        i.alreadyHave = False
                        money = money + moneyMade + i.amountBought
                        i.amountBought = 0
                        await generalChannel.send('Selling of all of ' + i.symbol)
                        await generalChannel.send('Money made = ' + str(round(moneyMade, 2)))

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

                    change = (currentPrice - i.priceBoughtAt) / i.priceBoughtAt * i.amountBought
                    currentValue = i.amountBought + change
                    moneyMade = change - (i.amountBought * 0.015) - (currentValue * 0.015)
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
                averageLastSixteenth = 0
                priceAverage = 0
                currentPrice = (yf.Ticker(i.symbol).history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                if i.isUSD == True:
                    currentPrice = currentPrice * (yf.Ticker('CAD=X').history(period='1d', start='2020-1-1', end=datetime.datetime.now())).tail(1)['Close'].iloc[0]

                for j in range(dataPoints):
                    priceAverage = priceAverage + i.previousPrices[j]
                    average = average + i.data[j]
                    if j > lastQuarter:
                        averageLastQuarter = averageLastQuarter + i.data[j]

                    if j > lastSixteenth:
                        averageLastSixteenth = averageLastSixteenth + i.data[j]

                spending = money * limit
                average = average / dataPoints
                averageLastQuarter = averageLastQuarter / (dataPoints / 4)
                averageLastSixteenth = averageLastSixteenth / (dataPoints / 16)
                priceAverage = priceAverage / dataPoints
                potentialMoneyMade = (priceAverage - currentPrice) / currentPrice * spending - (spending * 0.015) * 2
                await context.message.channel.send('Average: ' + str(average))
                await context.message.channel.send('Last Quarter Average: ' + str(averageLastQuarter))
                await context.message.channel.send('Last Sixteenth Average: ' + str(averageLastSixteenth))
                await context.message.channel.send('Potential Money Made if Bought Now: ' + str(round(potentialMoneyMade, 2)))
                break

    except Exception as e:
        print("Info: " + str(e))

#Run the client on the server
client.run('ODA1NjEzMTczMzYwODIwMjc3.YBdbvA.M8upIcRfyRpDibiu9j81ic8mbC4')