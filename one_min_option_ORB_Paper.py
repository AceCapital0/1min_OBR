# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 12:15:31 2024

@author: Vinay Kumar
"""

import pandas as pd
import time
from datetime import datetime, time as t
import csv
from breeze_connect import BreezeConnect
import logging

# Initialize ICICI Breeze API
breeze = BreezeConnect(api_key="77%U3I71634^099gN232777%316Q~v4=")
breeze.generate_session(api_secret="9331K77(I8_52JG2K73$5438q95772j@",
                        session_token="47492870")

# Define trading parameters
Call_Buy = None
Put_Buy = None
factor = None
volume_high = None
volume_low = None
move_sl_to_cost = False
orb = False
time_1 = t(3, 47)  # 9:17 AM IST -> 3:47 AM UTC
time_2 = t(9, 45)  # 3:01 PM IST -> 9:31 AM UTC
target = 30
stoploss = 15
order = 0
quantity="100"
today = datetime.now().strftime("%Y-%m-%d")
fut_expiry  = "2024-09-26"
option_expiry_date = "2024-09-26"
expiry_date = f"{fut_expiry}T07:00:00.000Z"
option_expiry = f"{option_expiry_date}T07:00:00.000Z"


# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='Orb_paper_without_tgt_debug.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

log_file = "Orb_paper_without_tgt.csv"
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

def get_volume_factor(volume, avg_volume):
    """Determine the volume factor based on the current volume and average volume."""
    if volume > (avg_volume * 2.5):
        return True
    return None

def get_volume_factor2(volume, avg_volume):
    """Determine the volume factor based on the current volume and average volume."""
    if volume > (avg_volume * 2):
        return True
    return None

def adjust_trailing_sl(current_price, sl, order):
    """Adjust the trailing stop-loss based on the current price and factor."""
    if order in [1, -1]:
        new_sl = sl + 1
        return new_sl


def round_to_nearest_50(n):
    return round(n / 50) * 50

def update_volume_conditions(factor, last_row):
    """Update volume high and low based on the latest volume spike candle."""
    global volume_high, volume_low
    volume_high = last_row['high']
    volume_low = last_row['low']
    logging.info(f"{datetime.now()} Volume condition met with factor: {factor}, High={volume_high}, Low={volume_low}")

def update_volume_conditions2(factor, last_row, last_row2):
    """Update volume high and low based on the latest volume spike candle."""
    global volume_high, volume_low
    volume_high = max(last_row['high'], last_row2['high'])
    volume_low = min(last_row['low'], last_row2['low'])
    logging.info(f"{datetime.now()} Volume condition met with factor: {factor}, High={volume_high}, Low={volume_low}")

def retry_api_call(func, retries=5, delay=5, backoff=2):
    """Retry API calls with exponential backoff."""
    attempt = 0
    while attempt < retries:
        try:
            return func()
        except Exception as e:
            logging.error(f"Error during API call: {e}, Retrying in {delay} seconds...")
            attempt += 1
            time.sleep(delay)
            delay *= backoff
    raise Exception(f"API call failed after {retries} attempts.")

def get_historical_data_with_retry(interval, from_date, to_date, stock_code, exchange_code, product_type, expiry_date, right):
    return retry_api_call(
        lambda: breeze.get_historical_data_v2(interval=interval, from_date=from_date, to_date=to_date,
                                              stock_code=stock_code, exchange_code=exchange_code,
                                              product_type=product_type, expiry_date=expiry_date, right=right))

def get_quotes_with_retry(stock_code, exchange_code, product_type, right, strike_price):
    return retry_api_call(
        lambda: breeze.get_quotes(stock_code=stock_code, exchange_code=exchange_code,
                                  product_type=product_type, right=right, strike_price=strike_price))

def get_option_chain_quotes_with_retry(stock_code, exchange_code, product_type, expiry_date, right, strike_price):
    return retry_api_call(
        lambda: breeze.get_option_chain_quotes(stock_code=stock_code, exchange_code=exchange_code,
                                               product_type=product_type, expiry_date=expiry_date,
                                               right=right, strike_price=strike_price))
def get_future_quotes_with_retry(stock_code, exchange_code, product_type, expiry_date):
    return retry_api_call(
        lambda: breeze.get_option_chain_quotes(stock_code=stock_code, exchange_code=exchange_code,
                                               product_type=product_type, expiry_date=expiry_date))
def get_order_detail_with_retry(exchange_code, order_id):
    return retry_api_call(
        lambda: breeze.get_order_detail(exchange_code=exchange_code, order_id=order_id))    

# Check for past ORB breakout
orb_breakout_occurred = False
if order == 0:
    olhc = breeze.get_historical_data_v2(interval="1minute",
                            from_date= f"{today}T09:15:00.000Z",
                            to_date= f"{today}T15:30:00.000Z",
                            stock_code="NIFTY",
                            exchange_code="NFO",
                            product_type="futures",
                            expiry_date= expiry_date,
                            right="others")
    
    olhc = pd.DataFrame(olhc['Success'])
    
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
        
        olhc = get_historical_data_with_retry(interval="1minute",
                                      from_date=f"{today}T09:15:00.000Z",
                                      to_date=f"{today}T15:30:00.000Z",
                                      stock_code="NIFTY",
                                      exchange_code="NFO",
                                      product_type="futures",
                                      expiry_date=expiry_date,
                                      right="others")
        
        olhc = pd.DataFrame(olhc['Success'])
        first_row = olhc.iloc[0]
        last_row = olhc.iloc[-1]
        
        if first_row['high'] < last_row['close']:
            breakout_candle_high = first_row['high']
            breakout_highs = olhc[olhc['high'] > breakout_candle_high]
            if not breakout_highs.empty:
                breakout_high = breakout_highs.iloc[0]['high']
                subsequent_highs = olhc[olhc['high'] > breakout_high]
                if not subsequent_highs.empty:
                    current_time = datetime.now()

                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    # Buy condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="call", strike_price=strike_price)
                    
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 

                    Call_Buy = round(premium, 2)
                    right = 'BUY'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Call_Buy + target
                    sl = Call_Buy - stoploss  # Set initial SL
                    order = 1
                    orb = True
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"Call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"Call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
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
                    current_time = datetime.now()
                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    
                    # Sell condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="put", strike_price=strike_price)
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 

                    Put_Buy = round(premium, 2)
                    right = 'SELL'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Put_Buy + target
                    sl = Put_Buy - stoploss  # Set initial SL
                    order = -1
                    orb = True
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
            else:
                print("No Bearish Position")
                logging.info("No Bearish Position")
        print("ORB Checking")

    # Check for volume-based re-entry
    if order == 2 and time_1 < t(now.hour, now.minute) < time_2 and now.second == 0:
        time.sleep(5)
        print(f"Checking Volume-Based Re-entry at {now}")
        logging.info(f"Checking Volume-Based Re-entry at {now}")       
        # Fetch updated OHLC data
        vol_hist = get_historical_data_with_retry(interval="1minute",
                                      from_date=f"{today}T09:15:00.000Z",
                                      to_date=f"{today}T15:30:00.000Z",
                                      stock_code="NIFTY",
                                      exchange_code="NFO",
                                      product_type="futures",
                                      expiry_date=expiry_date,
                                      right="others")
        olhc = pd.DataFrame(vol_hist['Success'])
        avg_volume = olhc['volume'].ewm(span=10, min_periods=10).mean().iloc[-2]  # Use second last row for previous candle's EMA
        last_row = olhc.iloc[-2]  # Last completed candle
        factor = get_volume_factor(last_row['volume'], avg_volume)
        avg_volume2 = olhc['volume'].ewm(span=10, min_periods=10).mean().iloc[-3]  # Use second last row for previous candle's EMA
        last_row2 = olhc.iloc[-3]  # Last completed candle
        mul1 = get_volume_factor2(last_row2['volume'], avg_volume2)
        mul2 = get_volume_factor2(last_row['volume'], avg_volume)
        print(f"Volume-Based Re-entry with factor {factor}, {now}. Last close: {last_row['close']}, last volume: {last_row['volume']}, avg volume: {avg_volume}")
        
        if factor:
            print(f"factor {factor}, {now}. Last close: {last_row['close']}, last volume: {last_row['volume']}, avg volume: {avg_volume}")
            update_volume_conditions(factor, last_row)
            candle_count = 0
            while candle_count < 10:
                time.sleep(1)
                current_time = datetime.now()
                olhc = breeze.get_historical_data_v2(interval="1minute",
                                                    from_date= f"{today}T09:15:00.000Z",
                                                    to_date= f"{today}T15:30:00.000Z",
                                                    stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product_type="futures",
                                                    expiry_date = expiry_date,
                                                    right="others")
                olhc = pd.DataFrame(olhc['Success'])
                latest_candle = olhc.iloc[-1]

                # Check if breakout conditions are met
                if latest_candle['close'] > volume_high:
                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    # Call Buy condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="call", strike_price=strike_price)
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 
                    
                    Call_Buy = round(premium, 2)
                    right = 'Call_Buy'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Call_Buy + target
                    sl = Call_Buy - stoploss
                    order = 1
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"{now} Volume-Based call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    break
                
                elif latest_candle['close'] < volume_low:
                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    
                    # Put Buy condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="put", strike_price=strike_price)
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 
    
                    Put_Buy = round(premium, 2)
                    right = 'Put_Buy'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Put_Buy + target
                    sl = Put_Buy - stoploss
                    order = -1
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"{now} Volume-Based Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    break
                candle_count += 1
                time.sleep(60)
                
        elif mul1 and mul2:
            print(f"Two candle match {now}. 1st close: {last_row2['close']} 2nd close: {last_row['close']}, volumes: {last_row2['volume']}, {last_row['volume']}, volumes: {avg_volume2}, {avg_volume}")
            update_volume_conditions2(factor, last_row, last_row2)
            candle_count = 0
            while candle_count < 10:
                time.sleep(1)
                current_time = datetime.now()
                olhc = breeze.get_historical_data_v2(interval="1minute",
                                                    from_date= f"{today}T09:15:00.000Z",
                                                    to_date= f"{today}T15:30:00.000Z",
                                                    stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product_type="futures",
                                                    expiry_date = expiry_date,
                                                    right="others")
                olhc = pd.DataFrame(olhc['Success'])
                latest_candle = olhc.iloc[-1]

                # Check if breakout conditions are met
                if latest_candle['close'] > volume_high:
                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    # Call Buy condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="call", strike_price=strike_price)
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 
                    
                    Call_Buy = round(premium, 2)
                    right = 'Call_Buy'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Call_Buy + target
                    sl = Call_Buy - stoploss
                    order = 1
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"{now} Volume-Based call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Call Buy at: {Call_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    break
                
                elif latest_candle['close'] < volume_low:
                    ltp = get_quotes_with_retry(stock_code="NIFTY", exchange_code="NSE",
                                                product_type="cash", right="others", strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    
                    # Put Buy condition met
                    detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                                product_type="options", expiry_date=option_expiry,
                                                                right="put", strike_price=strike_price)
                    price = pd.DataFrame(detail['Success'])
                    premium = price['ltp'][0] 
    
                    Put_Buy = round(premium, 2)
                    right = 'Put_Buy'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = Put_Buy + target
                    sl = Put_Buy - stoploss
                    order = -1
                    entry_time = datetime.strptime(entry_time, '%H:%M:%S')
                    entry_time = current_time.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second, microsecond=0)
                    print(f"{now} Volume-Based Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Put Buy at: {Put_Buy}, strike_price: {strike_price}, Target: {tgt}, Stoploss: {sl}")
                    break
                candle_count += 1
                time.sleep(60)
                
    # Exit Conditions
    if order in [1, -1]:
        print(f"Checking exit conditions at {now}")
        logging.info(f"Checking exit conditions at {now}")
        time.sleep(5)
        current_time = datetime.now()
    
        time_difference = (current_time - entry_time).total_seconds() / 60
        #print(time_difference)
        exit_reason = ''
        if order == 1: 
            #logging.info(f"Updating Trailing SL at {now}")
        
            detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                        product_type="options", expiry_date=option_expiry,
                                                        right="call", strike_price=strike_price)
            ltp = pd.DataFrame(detail['Success'])
            premium = ltp['ltp'][0] 
            
            if premium >= sl + 1 + 15:
                sl = adjust_trailing_sl(premium, sl, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                

            if premium <= sl:
                exit_reason = 'Stoploss Hit'
            elif time_difference > 30:
                exit_reason = '30 candle hit'
            elif t(now.hour, now.minute) == t(15, 20):
                exit_reason = 'Market Close'
                
        elif order == -1:
            detail = get_option_chain_quotes_with_retry(stock_code="NIFTY", exchange_code="NFO",
                                                        product_type="options", expiry_date=option_expiry,
                                                        right="put", strike_price=strike_price)
            ltp = pd.DataFrame(detail['Success'])
            premium = ltp['ltp'][0] 
            
            if premium >= sl + 1 + 15:
                sl = adjust_trailing_sl(premium, sl, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                

            if premium <= sl:
                exit_reason = 'Stoploss Hit'
            elif time_difference > 30:
                exit_reason = '30 candle hit'
            elif t(now.hour, now.minute) == t(15, 20):
                exit_reason = 'Market Close'
        
        if exit_reason:
            print(f"{exit_reason}. Exiting position.")
            logging.info(f"{exit_reason}. Exiting position.")
            exit_time = datetime.now().strftime('%H:%M:%S')
            print(f"Exit Time: {exit_time}, strike_price: {strike_price}, LTP: {premium}")
            logging.info(f"Exit Time: {exit_time}, strike_price: {strike_price}, LTP: {premium}")
            
            # Calculate PNL
            pnl = (premium - Call_Buy) if order == 1 else (premium - Put_Buy)
            
            # Log trade details to CSV
            log_trade_to_csv(today, entry_time, Call_Buy if order == 1 else Put_Buy, right, premium, exit_time, exit_reason, pnl)
            
            order = 2

    time.sleep(1)
