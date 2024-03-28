from datetime import datetime
import pandas as pd
import yfinance as yf
import re
import requests
import warnings
from tabulate import tabulate
from stock_list import tickers


warnings.filterwarnings(
    "ignore",
    message="The 'unit' keyword in TimedeltaIndex construction is deprecated",
    category=FutureWarning,
    module="yfinance",
)
warnings.filterwarnings(
    "ignore",
    message="Series.__getitem__ treating keys as positions is deprecated",
    category=FutureWarning,
    module="yfinance",
)


def find_previous(data, current_index):
    prev_swing = None
    for i in range(current_index - 1, -1, -1):
        if data.loc[i, 'swing'] == 'll' or data.loc[i, 'swing'] == 'hl':
            prev_swing = data.loc[i]
            break
    return prev_swing


def calculate_swing_points(data):
    data['swing'] = ''
    for i in range(3, len(data) - 3):
        if (data['high'].iloc[i] > data['high'].iloc[i - 1]) and \
                (data['high'].iloc[i] > data['high'].iloc[i - 2]) and \
                (data['high'].iloc[i] > data['high'].iloc[i - 3]) and \
                (data['high'].iloc[i] > data['high'].iloc[i + 1]) and \
                (data['high'].iloc[i] > data['high'].iloc[i + 2]) and \
                (data['high'].iloc[i] > data['high'].iloc[i + 3]):
            data.at[i, 'swing'] = 'hh'
        elif (data['low'].iloc[i] < data['low'].iloc[i - 1]) and \
                (data['low'].iloc[i] < data['low'].iloc[i - 2]) and \
                (data['low'].iloc[i] < data['low'].iloc[i - 3]) and \
                (data['low'].iloc[i] < data['low'].iloc[i + 1]) and \
                (data['low'].iloc[i] < data['low'].iloc[i + 2]) and \
                (data['low'].iloc[i] < data['low'].iloc[i + 3]):
            data.at[i, 'swing'] = 'll'
    return data


def telegram_bot_sendtext(bot_message):
    bot_token = '944424320:AAFmEVyfAf3ssgemJZ2GGpXzD05vuanjAaY'
    bot_chatID = "-374237788"  # jojo
    # bot_token = '944424320:AAFmEVyfAf3ssgemJZ2GGpXzD05vuanjAaY'
    # bot_chatID = "-374237788"  # jojo
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message
    response = requests.get(send_text)
    return response.json()


def get_current_price(stock_name):
    data1 = yf.Ticker(stock_name)
    current_price = float(data1.history(period='1d')['Close'][0])
    # print(current_price,stock_name)
    return round(current_price, 2)

def check_valid_entry(data,signal):
    valid_order=True
    signal_time = pd.to_datetime(signal['time'])
    stop_loss = signal['stop_loss']
    for i in range(len(data)):
        if pd.to_datetime(data['time'].iloc[i]) > signal_time and data['low'].iloc[i] <= stop_loss:
            valid_order = False
            break
    return valid_order

def get_order_details(ticker):
    # data = yf.download(ticker, start="2024-01-01", end=datetime.now().strftime('%Y-%m-%d'))#, interval="1wk")
    data = yf.download(ticker, period="36mo", interval="1d")
    data.reset_index(inplace=True)
    data.rename(columns={'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)

    data = calculate_swing_points(data)
    z = 0
    higharray = []
    for i in range(len(data)):
        if data.swing[i] == 'hh':
            higharray.append([z, float(data.high[i])])
            if z > 0:
                if higharray[z][1] > higharray[z - 1][1]:
                    data.at[i, 'swing'] = 'hh'
                else:
                    data.at[i, 'swing'] = 'lh'
            else:
                data.at[i, 'swing'] = 'hh'
            z = z + 1

    z = 0
    lowarray = []
    for i in range(len(data)):
        if data.swing[i] == 'll':
            lowarray.append([z, float(data.low[i])])
            if z > 0:
                if lowarray[z][1] < lowarray[z - 1][1]:
                    data.at[i, 'swing'] = 'll'
                else:
                    data.at[i, 'swing'] = 'hl'
            else:
                data.at[i, 'swing'] = 'll'
            z = z + 1
    # print(tabulate(data, headers='keys', tablefmt='psql'))
    order_queue = []

    for i in range(2, len(data)):
        if data.loc[i, 'swing'] == 'hh':
            prev_swing = find_previous(data, i)
            if prev_swing is not None:
                if prev_swing['swing'] == 'll' or prev_swing['swing'] == 'hl':
                    entry = prev_swing['high']
                    stoploss = prev_swing['low']
                    swing = prev_swing['swing']+'hh'
                    hld = round(((float(data.loc[i, 'low']) - float(stoploss)) / float(entry)) * 100, 2)
                    candle_height = round((float(entry) - float(stoploss)) * 2, 2)  # for distance change last number
                    candle_height_entry = round((float(entry) - float(stoploss)) * 2, 2)  # for entry change
                    if float(data.loc[i, 'low']) >= (float(entry) + candle_height):
                        curret_p = get_current_price(ticker)
                        if float(stoploss)<curret_p<=float(entry)+float(candle_height_entry):
                            order_details = {
                                'ticker': ticker,
                                'time': prev_swing['time'],
                                'order_price': entry,
                                'stop_loss': stoploss
                            }
                            if check_valid_entry(data,order_details):
                                telegram_bot_sendtext(f"Ticker: {ticker},time: {prev_swing['time']}, Pattern: {swing}, "
                                                      f"hld: {str(hld)}")
                            order_queue.append(order_details)
    return order_queue


def main():
    # tickers = ['ALBERTDAVD.NS']
    for ticker in tickers:
        # print(ticker)
        try:
            order_queue = get_order_details(ticker)
            print(order_queue)
            # for order in order_queue:
            #     print(order)
        except Exception as e:
            print(e)


if __name__ == "__main__":
    main()
