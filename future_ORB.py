# -*- coding: utf-8 -*-
"""
Created on Wed Jul 31 11:06:54 2024

@author: Vinay Kumar
"""

import pandas as pd
import time
from datetime import datetime, time as t
from zerodha import Zerodha
import csv
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='trading_paper_debug.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize Zerodha API
kite = Zerodha(user_id='NX5644', password='Sanjay400@', twofa='Z2RKD6DPOV3GRL3DKLOFU44I76G3LVMI')
kite.login()

# Define trading parameters
time_1 = t(9, 17)
time_2 = t(15, 1)
fut_expiry = 'NIFTY24AUGFUT'
target = 30
stoploss = 15
order = 2
today = datetime.now().strftime('%Y-%m-%d')

log_file = "Future_ORB_paper.csv"
headers = ['Date', 'Time', 'Entry Price', 'BUY/SELL', 'Exit Price', 'Exit Time', 'Exit Reason', 'PNL']


# Create file and write headers if file doesn't exist
try:
    with open(log_file, 'x', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
except FileExistsError:
    pass

# Function to log trade information to CSV
def log_trade_to_csv(today, entry_time, entry_price, direction, exit_price, exit_time, exit_reason, pnl):
    with open(log_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([today, entry_time, entry_price, direction, exit_price, exit_time, exit_reason, pnl])

# Get instrument details
instruments = pd.DataFrame(kite.instruments())
instruments.to_csv('instruments.csv')
instruments = pd.read_csv('instruments.csv')
instruments1 = instruments[(instruments.tradingsymbol == fut_expiry)]
underlying_inst_id = instruments1.iloc[0]['instrument_token']

buy_future = None
sell_future = None
factor = None
volume_high = None
volume_low = None
volume_spike_time = None
orb = False

def get_volume_factor(volume, avg_volume):
    """Determine the volume factor based on the current volume and average volume."""
    if volume > (avg_volume * 3.5):
        return 10
    elif volume > (avg_volume * 3):
        return 7.5
    elif volume > (avg_volume * 2.5):
        return 5
    return None

def adjust_trailing_sl(current_price, sl, factor, order):
    """Adjust the trailing stop-loss based on the current price and factor."""
    if order == 1:  # Long position
        new_sl = sl + factor
        if current_price >= sl + 15 + factor:
            return new_sl
    elif order == -1:  # Short position
        new_sl = sl - factor
        if current_price <= sl - 15 - factor:
            return new_sl
    return sl


def adjust_trailing_sl_orb(current_price, sl, order):
    """Adjust the trailing stop-loss based on the current price for ORB."""
    if order == 1:  # Long position
        if current_price >= sl + 15:
            return current_price - 15
    elif order == -1:  # Short position
        if current_price <= sl - 15:
            return current_price + 15
    return sl

def update_volume_conditions(factor, last_row):
    """Update volume high and low based on the latest volume spike candle."""
    global volume_high, volume_low
    volume_high = last_row['high']
    volume_low = last_row['low']
    logging.info(f"{datetime.now()} Volume condition met with factor: {factor}, High={volume_high}, Low={volume_low}")

# Check for past ORB breakout
orb_breakout_occurred = False
if order == 0:
    olhc = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=today, interval="minute")
    olhc = pd.DataFrame(olhc)
    
    if len(olhc) > 0:
        first_row = olhc.iloc[0]
        breakout_highs = olhc[olhc['high'] > first_row['high']]
        breakout_lows = olhc[olhc['low'] < first_row['low']]
        
        # Check if there's a subsequent candle that confirms the ORB breakout
        if not breakout_highs.empty:
            breakout_high = breakout_highs.iloc[0]['high']
            subsequent_highs = olhc[olhc['high'] > breakout_high]
            if not subsequent_highs.empty:
                orb_breakout_occurred = True
                print("ORB breakout and subsequent high already occurred before script start. Skipping ORB and proceeding to volume-based entries.")
                logging.info("ORB breakout and subsequent high already occurred before script start. Skipping ORB and proceeding to volume-based entries.")
                
        if not breakout_lows.empty:
            breakout_low = breakout_lows.iloc[0]['low']
            subsequent_lows = olhc[olhc['low'] < breakout_low]
            if not subsequent_lows.empty:
                orb_breakout_occurred = True
                print("ORB breakout and subsequent low already occurred before script start. Skipping ORB and proceeding to volume-based entries.")
                logging.info("ORB breakout and subsequent low already occurred before script start. Skipping ORB and proceeding to volume-based entries.")
    if orb_breakout_occurred:
        order = 2
        
# Main loop
while True:
    now = datetime.now()

    # ORB Breakout Condition
    if not orb_breakout_occurred and time_1 < t(now.hour, now.minute) < time_2 and order == 0 and now.second == 1:
        print(f"Checking ORB conditions at {now}")
        logging.info(f"Checking ORB conditions at {now}")

        time.sleep(1)
        olhc = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=today, interval="minute")
        olhc = pd.DataFrame(olhc)
        first_row = olhc.iloc[0]
        last_row = olhc.iloc[-1]
        
        if first_row['high'] < last_row['close']:
            breakout_candle_high = first_row['high']
            breakout_highs = olhc[olhc['high'] > breakout_candle_high]
            if not breakout_highs.empty:
                breakout_high = breakout_highs.iloc[0]['high']
                subsequent_highs = olhc[olhc['high'] > breakout_high]
                if not subsequent_highs.empty:
                    for j in range(0, 5):
                        try:
                            ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                            ltp = pd.DataFrame(ltp)
                            premium = ltp['close'][0]
                            break
                        except:
                            pass
                    buy_future = round(premium, 2)
                    right = 'BUY'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = buy_future + target
                    sl = buy_future - stoploss  # Set initial SL
                    order = 1
                    orb = True
                    print(f"Buy Future at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"Buy Future at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
            else:
                print("No Bullish Position")
                logging.info("No Bullish Position")
        
        if first_row['low'] > last_row['close']:
            breakout_candle_low = first_row['low']
            breakout_lows = olhc[olhc['low'] < breakout_candle_low]
            if not breakout_lows.empty:
                breakout_low = breakout_lows.iloc[0]['low']
                subsequent_lows = olhc[olhc['low'] < breakout_low]
                if not subsequent_lows.empty:
                    for j in range(0, 5):
                        try:
                            ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                            ltp = pd.DataFrame(ltp)
                            premium = ltp['close'][0]
                            break
                        except:
                            pass
                    sell_future = round(premium, 2)
                    right = 'SELL'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = sell_future - target
                    sl = sell_future + stoploss  # Set initial SL
                    order = -1
                    orb = True
                    print(f"Sell Future at: {sell_future}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"Sell Future at: {sell_future}, Target: {tgt}, Stoploss: {sl}")
            else:
                print("No Bearish Position")
                logging.info("No Bearish Position")
        print("ORB Checking")
    
    # Exit Conditions
    if order in [1, -1]:
        print(f"Checking exit conditions at {now}")
        logging.info(f"Checking exit conditions at {now}")
        time.sleep(5)
        for j in range(0, 5):
            try:
                ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                ltp = pd.DataFrame(ltp)
                premium = ltp['close'][0]
                break
            except:
                pass

        exit_reason = ''
        if order == 1:
            if premium >= tgt:
                exit_reason = 'Target Hit'
            elif premium <= sl:
                exit_reason = 'Stoploss Hit'
            elif t(now.hour, now.minute) == t(15, 20):
                exit_reason = 'Market Close'
        elif order == -1:
            if premium <= tgt:
                exit_reason = 'Target Hit'
            elif premium >= sl:
                exit_reason = 'Stoploss Hit'
            elif t(now.hour, now.minute) == t(15, 20):
                exit_reason = 'Market Close'
        
        if exit_reason:
            print(f"{exit_reason}. Exiting position.")
            logging.info(f"{exit_reason}. Exiting position.")
            exit_time = datetime.now().strftime('%H:%M:%S')
            print(f"Exit Time: {exit_time}, LTP: {premium}")
            logging.info(f"Exit Time: {exit_time}, LTP: {premium}")
            
            # Calculate PNL
            pnl = (premium - buy_future) if order == 1 else (sell_future - premium)
            
            # Log trade details to CSV
            log_trade_to_csv(today, entry_time, buy_future if order == 1 else sell_future, right, premium, exit_time, exit_reason, pnl)
            
            order = 2
            orb = False
        else:
            if orb:
                sl = adjust_trailing_sl_orb(premium, sl, order)
                print(f"Trailing Stoploss adjusted to {sl} at price {premium}")
                logging.info(f"Trailing Stoploss adjusted to {sl} at price {premium}")

    # Check for volume-based re-entry
    if order == 2 and time_1 < t(now.hour, now.minute) < time_2 and now.second == 0:
        time.sleep(1)
        print(f"Checking Volume-Based Re-entry at {now}")
        logging.info(f"Checking Volume-Based Re-entry at {now}")       
        # Fetch updated OHLC data
        olhc = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=today, interval="minute")
        olhc = pd.DataFrame(olhc)
        avg_volume = olhc['volume'].ewm(span=10, min_periods=10).mean().iloc[-2]  # Use second last row for previous candle's EMA
        last_row = olhc.iloc[-2]  # Last completed candle

        factor = get_volume_factor(last_row['volume'], avg_volume)
        print(f"Volume-Based Re-entry with factor {factor}. Last close: {last_row['close']}, last volume: {last_row['volume']}, avg volume: {avg_volume}")
        if factor:
            update_volume_conditions(factor, last_row)

            candle_count = 0  # Initialize candle count
            # Continuously check for breakouts within the 10-candle window
            while candle_count < 10:
                # Fetch updated OHLC data for real-time checking
                olhc = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=today, interval="minute")
                olhc = pd.DataFrame(olhc)
                latest_candle = olhc.iloc[-1]

                # Check if breakout conditions are met
                if latest_candle['close'] > volume_high:
                    # Buy condition met
                    for _ in range(5):
                        try:
                            ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                            ltp = pd.DataFrame(ltp)
                            premium = ltp['close'][0]
                            break
                        except Exception as e:
                            logging.error(f"Error fetching LTP: {e}")
                            time.sleep(1)
                    buy_future = round(premium, 2)
                    right = 'BUY'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = buy_future + target
                    sl = buy_future - stoploss
                    move_sl_to_cost = False
                    order = 1
                    print(f"{now} Volume-Based Buy at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Buy at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
                    break

                elif latest_candle['close'] < volume_low:
                    # Sell condition met
                    for _ in range(5):
                        try:
                            ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                            ltp = pd.DataFrame(ltp)
                            premium = ltp['close'][0]
                            break
                        except Exception as e:
                            logging.error(f"Error fetching LTP: {e}")
                            time.sleep(1)
                    sell_future = round(premium, 2)
                    right = 'SELL'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = sell_future - target
                    sl = sell_future + stoploss
                    move_sl_to_cost = False
                    order = -1
                    print(f"{now} Volume-Based Sell at: {sell_future}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Sell at: {sell_future}, Target: {tgt}, Stoploss: {sl}")
                    break

                # Increment candle count
                candle_count += 1
                time.sleep(60)


    # Update Trailing SL
    if factor and order in [1, -1]:
        #logging.info(f"Updating Trailing SL at {now}")
        for j in range(0, 5):
            try:
                ltp = kite.historical_data(instrument_token=underlying_inst_id, from_date=today, to_date=now, interval="day")
                ltp = pd.DataFrame(ltp)
                premium = ltp['close'][0]
                break
            except:
                pass
    
        if order == 1:  # Long position
            if not move_sl_to_cost and premium >= buy_future + 15:
                sl = buy_future  # Move SL to cost
                move_sl_to_cost = True  # Set the flag after moving SL to cost
                print(f"Stop Loss moved to cost. Premium: {premium}, Cost SL: {sl}")
                logging.info(f"Stop Loss moved to cost. Premium: {premium}, New SL: {sl}")
            elif move_sl_to_cost and premium >= sl + factor + 15:
                sl = adjust_trailing_sl(premium, sl, factor, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
    
        if order == -1:  # Short position
            if not move_sl_to_cost and premium <= sell_future - 15:
                sl = sell_future  # Move SL to cost
                move_sl_to_cost = True  # Set the flag after moving SL to cost
                print(f"Stop Loss moved to cost. Premium: {premium}, Cost SL: {sl}")
                logging.info(f"Stop Loss moved to cost. Premium: {premium}, New SL: {sl}")
            elif move_sl_to_cost and premium <= sl - factor - 15:
                sl = adjust_trailing_sl(premium, sl, factor, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")


    time.sleep(1)  # Sleep to avoid rapid API call
