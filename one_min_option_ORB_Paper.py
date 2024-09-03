# -*- coding: utf-8 -*-
"""
Created on Mon Aug 26 12:15:31 2024

@author: Vinay Kumar
"""

import pandas as pd
import time
from datetime import datetime, timedelta, time as t
import csv
from breeze_connect import BreezeConnect
import logging

# Initialize ICICI Breeze API
breeze = BreezeConnect(api_key="S43813906421*qTB5O98pn4i5r386290")  # Replace with your API key
breeze.generate_session(api_secret="2pc136H426=9j7o+32(67179+C19Ba99", session_token="46626435")  

# Define trading parameters
Call_Buy = None
Put_Buy = None
factor = None
volume_high = None
volume_low = None
move_sl_to_cost = False
orb = False
time_1 = t(3, 47)  # 9:17 AM IST -> 3:47 AM UTC
time_2 = t(9, 31)  # 3:01 PM IST -> 9:31 AM UTC
target = 30
stoploss = 15
order = 0
quantity="25"
today = datetime.now().strftime("%Y-%m-%d")
fut_expiry  = "2024-09-26"
option_expiry_date = "2024-09-05"
expiry_date = f"{fut_expiry}T07:00:00.000Z"
option_expiry = f"{option_expiry_date}T07:00:00.000Z"

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='1min_Orb_paper_trading_debug.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

log_file = "1min_Orb_paper_trading.csv"
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
        return 2
    return None

def adjust_trailing_sl(current_price, sl, factor, order):
    """Adjust the trailing stop-loss based on the current price and factor."""
    if order == 1:  # Long position
        new_sl = sl + factor
        return new_sl
    elif order == -1:  # Short position
        new_sl = sl + factor
        return new_sl
    return sl

def round_to_nearest_50(n):
    return round(n / 50) * 50

def adjust_trailing_sl_orb(current_price, sl, order):
    """Adjust the trailing stop-loss based on the current price for ORB."""
    if order == 1:  # Long position
        if current_price >= sl + 15:
            return current_price - 15
    elif order == -1:  # Short position
        if current_price >= sl + 15:
            return current_price - 15
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
        for j in range(0, 5):
            try:
                Orb_hist = breeze.get_historical_data_v2(interval="1minute",
                                    from_date= f"{today}T09:15:00.000Z",
                                    to_date= f"{today}T15:30:00.000Z",
                                    stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product_type="futures",
                                    expiry_date = expiry_date,
                                    right="others")
            except:
                pass
        olhc = pd.DataFrame(Orb_hist['Success'])
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

                    ltp = breeze.get_quotes(stock_code="NIFTY",
                                            exchange_code="NSE",
                                            product_type="cash",
                                            right="others",
                                            strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    # Buy condition met
                    detail = breeze.place_order(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product="options",
                                                action="buy",
                                                order_type="market",
                                                stoploss="",
                                                quantity=quantity,
                                                price="",
                                                validity="day",
                                                disclosed_quantity="0",
                                                expiry_date=option_expiry,
                                                right="call",
                                                strike_price=strike_price)
                    ord_id = detail['Success']
                    order_id = ord_id['order_id']
                    ltp = breeze.get_order_detail(exchange_code="NFO",order_id=order_id)
                    ltp = pd.DataFrame(ltp['Success'])
                    premium = float(ltp['price'][0])

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
                    ltp = breeze.get_quotes(stock_code="NIFTY",
                                            exchange_code="NSE",
                                            product_type="cash",
                                            right="others",
                                            strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    
                    # Sell condition met
                    detail = breeze.place_order(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product="options",
                                                action="buy",
                                                order_type="market",
                                                stoploss="",
                                                quantity=quantity,
                                                price="",
                                                validity="day",
                                                disclosed_quantity="0",
                                                expiry_date=option_expiry,
                                                right="put",
                                                strike_price=strike_price)
                    ord_id = detail['Success']
                    order_id = ord_id['order_id']
                    ltp = breeze.get_order_detail(exchange_code="NFO",order_id=order_id)
                    ltp = pd.DataFrame(ltp['Success'])
                    premium = float(ltp['price'][0])

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
        
            ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product_type="options",
                                                expiry_date=option_expiry,
                                                right="call",
                                                strike_price=strike_price)
            ltp = pd.DataFrame(ltp['Success'])
            premium = ltp['ltp'][0] 
            if premium >= tgt:
                exit_reason = 'Target Hit'
            elif premium <= sl:
                exit_reason = 'Stoploss Hit'
            elif time_difference > 30:
                exit_reason = '30 candle hit'
            elif t(now.hour, now.minute) == t(9, 50):
                exit_reason = 'Market Close'
        elif order == -1:
            ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product_type="options",
                                                expiry_date=option_expiry,
                                                right="put",
                                                strike_price=strike_price)
            ltp = pd.DataFrame(ltp['Success'])
            premium = ltp['ltp'][0] 
            if premium >= tgt:
                exit_reason = 'Target Hit'
            elif premium <= sl:
                exit_reason = 'Stoploss Hit'
            elif time_difference > 30:
                exit_reason = '30 candle hit'
            elif t(now.hour, now.minute) == t(9, 50):
                exit_reason = 'Market Close'
        
        if exit_reason:
            print(f"{exit_reason}. Exiting position.")
            logging.info(f"{exit_reason}. Exiting position.")
            exit_time = datetime.now().strftime('%H:%M:%S')
            print(f"Exit Time: {exit_time}, strike_price: {strike_price}, LTP: {premium}")
            logging.info(f"Exit Time: {exit_time}, strike_price: {strike_price}, LTP: {premium}")
            
            # Calculate PNL
            pnl = (premium - Call_Buy) if order == 1 else (Put_Buy - premium)
            
            # Log trade details to CSV
            log_trade_to_csv(today, entry_time, Call_Buy if order == 1 else Put_Buy, right, premium, exit_time, exit_reason, pnl)
            
            order = 2
            orb = False
        else:
            if orb:
                sl = adjust_trailing_sl_orb(premium, sl, order)
                print(f"Trailing Stoploss adjusted to {sl} at price {premium}")
                logging.info(f"Trailing Stoploss adjusted to {sl} at price {premium}")

    # Check for volume-based re-entry
    if order == 2 and time_1 < t(now.hour, now.minute) < time_2 and now.second == 0:
        time.sleep(5)
        print(f"Checking Volume-Based Re-entry at {now}")
        logging.info(f"Checking Volume-Based Re-entry at {now}")       
        # Fetch updated OHLC data
        for j in range(0, 5):
            try:
                vol_hist = breeze.get_historical_data_v2(interval="1minute",
                                                        from_date= f"{today}T09:15:00.000Z",
                                                        to_date= f"{today}T15:30:00.000Z",
                                                        stock_code="NIFTY",
                                                        exchange_code="NFO",
                                                        product_type="futures",
                                                        expiry_date = expiry_date,
                                                        right="others")
            except:
                pass 
        olhc = pd.DataFrame(vol_hist['Success'])
        avg_volume = olhc['volume'].ewm(span=10, min_periods=10).mean().iloc[-1]  # Use second last row for previous candle's EMA
        last_row = olhc.iloc[-1]  # Last completed candle
        factor = get_volume_factor(last_row['volume'], avg_volume)
        print(f"Volume-Based Re-entry with factor {factor}{now}. Last close: {last_row['close']}, last volume: {last_row['volume']}, avg volume: {avg_volume}")
        if factor:
            update_volume_conditions(factor, last_row)
            
            while True:
                time.sleep(1)
                current_time = datetime.now()
                for j in range(0, 5):
                    try:
                # Fetch updated OHLC data for real-time checking
                        df = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                             exchange_code="NFO",
                                                             product_type="futures",
                                                             expiry_date=expiry_date)
                    except:
                        pass 
                ltp = pd.DataFrame(df['Success'])
                latest_candle = ltp['ltp'][0]
                #print(volume_high, volume_low, latest_candle)    
                # Check if breakout conditions are met
                if latest_candle > volume_high:
                    ltp = breeze.get_quotes(stock_code="NIFTY",
                                            exchange_code="NSE",
                                            product_type="cash",
                                            right="others",
                                            strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    # Call Buy condition met
                    detail = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                        exchange_code="NFO",
                                                        product_type="options",
                                                        expiry_date=option_expiry,
                                                        right="call",
                                                        strike_price=strike_price)
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
                
                elif latest_candle < volume_low:
                    ltp = breeze.get_quotes(stock_code="NIFTY",
                                            exchange_code="NSE",
                                            product_type="cash",
                                            right="others",
                                            strike_price="0")
                    ltp = pd.DataFrame(ltp['Success'])
                    strike_price= round_to_nearest_50(ltp['ltp'][0])
                    
                    # Put Buy condition met
                    detail = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                        exchange_code="NFO",
                                                        product_type="options",
                                                        expiry_date=option_expiry,
                                                        right="put",
                                                        strike_price=strike_price)
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
                
    # Update Trailing SL
    if factor and order in [1, -1]:
        #logging.info(f"Updating Trailing SL at {now}")
        if order == 1:  # Long position
            ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product_type="options",
                                                expiry_date=option_expiry,
                                                right="call",
                                                strike_price=strike_price)
            ltp = pd.DataFrame(ltp['Success'])
            premium = ltp['ltp'][0] 
            if premium >= sl + factor + 15:
                sl = adjust_trailing_sl(premium, sl, factor, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
    
        if order == -1:  # Short position
            ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                exchange_code="NFO",
                                                product_type="options",
                                                expiry_date=option_expiry,
                                                right="put",
                                                strike_price=strike_price)
            ltp = pd.DataFrame(ltp['Success'])
            premium = ltp['ltp'][0] 
            if premium >= sl + factor + 15:
                sl = adjust_trailing_sl(premium, sl, factor, order)
                print(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")
                logging.info(f"Stop Loss trailed. Premium: {premium}, New SL: {sl}")

    time.sleep(1)
