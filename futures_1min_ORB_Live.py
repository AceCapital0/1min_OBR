# -*- coding: utf-8 -*-
"""
Created on Fri Aug 16 10:51:37 2024

@author: Vinay Kumar
"""
import pandas as pd
import time
from datetime import datetime, time as t
import csv
from breeze_connect import BreezeConnect
import logging
# Initialize ICICI Breeze API
breeze = BreezeConnect(api_key="S43813906421*qTB5O98pn4i5r386290")  # Replace with your API key
breeze.generate_session(api_secret="2pc136H426=9j7o+32(67179+C19Ba99", session_token="45915225")  

# Define trading parameters
buy_future = None
sell_future = None
factor = None
volume_high = None
volume_low = None
move_sl_to_cost = False
orb = False
time_1 = t(9, 17)
time_2 = t(15, 30)
target = 30
stoploss = 15
order = 0
quantity="25"
today = datetime.now().strftime("%Y-%m-%d")
expiry  = "2024-08-29"
expiry_date = f"{expiry}T07:00:00.000Z"

# Configure logging
logging.basicConfig(level=logging.DEBUG, filename='trading_debug.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')

log_file = "Future_ORB.csv"
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

        time.sleep(1)
        olhc = breeze.get_historical_data_v2(interval="1minute",
                            from_date= f"{today}T09:15:00.000Z",
                            to_date= f"{today}T15:30:00.000Z",
                            stock_code="NIFTY",
                            exchange_code="NFO",
                            product_type="futures",
                            expiry_date = expiry_date,
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
                    for j in range(0, 5):
                        try:
                            detail = breeze.place_order(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product="futures",
                                                    action="buy",
                                                    order_type="market",
                                                    stoploss="0",
                                                    quantity=quantity,
                                                    validity="day",
                                                    expiry_date=expiry_date,
                                                    right="others")
                            ord_id = pd.dataframe(detail['Success'])
                            order_id = ord_id['order_id'][0]
                            ltp = breeze.get_order_detail(exchange_code="NSE",order_id=order_id)
                            ltp = pd.DataFrame(ltp['Success'])
                            premium = ltp['execution_price'][0]
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
                            detail = breeze.place_order(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product="futures",
                                                    action="sell",
                                                    order_type="market",
                                                    stoploss="0",
                                                    quantity=quantity,
                                                    validity="day",
                                                    expiry_date=expiry_date,
                                                    right="others")
                            ord_id = pd.dataframe(detail['Success'])
                            order_id = ord_id['order_id'][0]
                            ltp = breeze.get_order_detail(exchange_code="NSE",order_id=order_id)
                            ltp = pd.DataFrame(ltp['Success'])
                            premium = ltp['execution_price'][0]
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
                ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product_type="futures",
                                                    expiry_date=expiry_date)
                ltp = pd.DataFrame(ltp['Success'])
                premium = ltp['ltp'][0]
                break
            except:
                pass

        exit_reason = ''
        if order == 1: 
            if premium >= tgt:
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="sell",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
                exit_reason = 'Target Hit'
            elif premium <= sl:
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="sell",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
                exit_reason = 'Stoploss Hit'
            elif t(now.hour, now.minute) == t(15, 20):
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="sell",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
                exit_reason = 'Market Close'
        elif order == -1:
            if premium <= tgt:
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="buy",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
                exit_reason = 'Target Hit'
            elif premium >= sl:
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="buy",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
                exit_reason = 'Stoploss Hit'
            elif t(now.hour, now.minute) == t(15, 20):
                breeze.place_order(stock_code="NIFTY",
                                    exchange_code="NFO",
                                    product="futures",
                                    action="buy",
                                    order_type="market",
                                    stoploss="0",
                                    quantity=quantity,
                                    validity="day",
                                    expiry_date=expiry_date,
                                    right="others")
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
        olhc = breeze.get_historical_data_v2(interval="1minute",
                            from_date= f"{today}T09:15:00.000Z",
                            to_date= f"{today}T15:30:00.000Z",
                            stock_code="NIFTY",
                            exchange_code="NFO",
                            product_type="futures",
                            expiry_date = expiry_date,
                            right="others")
        olhc = pd.DataFrame(olhc['Success'])
        avg_volume = olhc['volume'].ewm(span=10, min_periods=10).mean().iloc[-2]  # Use second last row for previous candle's EMA
        last_row = olhc.iloc[-2]  # Last completed candle

        factor = get_volume_factor(last_row['volume'], avg_volume)
        # print(f"Volume-Based Re-entry with factor {factor}. Last close: {last_row['close']}, last volume: {last_row['volume']}, avg volume: {avg_volume}")
        if factor:
            update_volume_conditions(factor, last_row)

            candle_count = 0  # Initialize candle count
            # Continuously check for breakouts within the 10-candle window
            while candle_count < 10:
                # Fetch updated OHLC data for real-time checking
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
                    # Buy condition met
                    for _ in range(5):
                        try:
                            detail = breeze.place_order(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product="futures",
                                                    action="buy",
                                                    order_type="market",
                                                    stoploss="0",
                                                    quantity=quantity,
                                                    validity="day",
                                                    expiry_date=expiry_date,
                                                    right="others")
                            ord_id = pd.dataframe(detail['Success'])
                            order_id = ord_id['order_id'][0]
                            ltp = breeze.get_order_detail(exchange_code="NSE",order_id=order_id)
                            ltp = pd.DataFrame(ltp['Success'])
                            premium = ltp['execution_price'][0]
                            break
                        except Exception as e:
                            logging.error(f"Error fetching LTP: {e}")
                            time.sleep(1)
                    buy_future = round(premium, 2)
                    right = 'BUY'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = buy_future + target
                    sl = buy_future - stoploss
                    order = 1
                    print(f"{now} Volume-Based Buy at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
                    logging.info(f"{now} Volume-Based Buy at: {buy_future}, Target: {tgt}, Stoploss: {sl}")
                    break

                elif latest_candle['close'] < volume_low:
                    # Sell condition met
                    for _ in range(5):
                        try:
                            detail = breeze.place_order(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product="futures",
                                                    action="sell",
                                                    order_type="market",
                                                    stoploss="0",
                                                    quantity=quantity,
                                                    validity="day",
                                                    expiry_date=expiry_date,
                                                    right="others")
                            ord_id = pd.dataframe(detail['Success'])
                            order_id = ord_id['order_id'][0]
                            ltp = breeze.get_order_detail(exchange_code="NSE",order_id=order_id)
                            ltp = pd.DataFrame(ltp['Success'])
                            premium = ltp['execution_price'][0]
                            break
                        except Exception as e:
                            logging.error(f"Error fetching LTP: {e}")
                            time.sleep(1)
                    sell_future = round(premium, 2)
                    right = 'SELL'
                    entry_time = datetime.now().strftime('%H:%M:%S')
                    tgt = sell_future - target
                    sl = sell_future + stoploss
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
                ltp = breeze.get_option_chain_quotes(stock_code="NIFTY",
                                                    exchange_code="NFO",
                                                    product_type="futures",
                                                    expiry_date=expiry_date)
                ltp = pd.DataFrame(ltp)
                premium = ltp['ltp'][0] 
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

    time.sleep(1)