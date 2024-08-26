# Nifty Futures 1min ORB Strategy

This Python script implements an automated trading strategy for Nifty Futures. The strategy focuses on an Opening Range Breakout (ORB) and volume-based entries for subsequent trades. The script interacts with the ICICI Breeze API to fetch real-time data, execute trades, and manage positions.

## Table of Contents

1. [Requirements](#requirements)
2. [Setup](#setup)
3. [Configuration](#configuration)
4. [Trading Logic](#trading-logic)
   - [Opening Range Breakout (ORB)](#opening-range-breakout-orb)
   - [Volume-Based Entries](#volume-based-entries)
   - [Trailing Stop-Loss](#trailing-stop-loss)
5. [Phase 2 Changes](#Phase-2-Changes)
   - [Volume Spike Criteria](#Volume-Spike-Criteria)
   - [Exit Strategy](#Exit-Strategy)
   - [Adjustments and Changes](#Adjustments-and-Changes)
6. [Logging Trades](#logging-trades)
7. [Execution](#execution)
8. [License](#license)

## Requirements

- Python 3.x
- Pandas
- ICICI Breeze API
- CSV module
- Logging module

## Setup

1. **Install required libraries:**

   ```bash
   pip install pandas
   ```

2. **ICICI Breeze API Integration:**
   Ensure you have access to the ICICI Breeze API. Configure your API keys in the script where needed.

## Configuration

### Parameters

- `quantity`: Number of Nifty Future contracts to trade.
- `target`: Target profit in points.
- `stoploss`: Stop-loss in points.
- `expiry_date`: Expiry date for the Nifty Future contract.

### File Paths

- `log_file`: Path to the CSV file where trades will be logged.

### Time Variables

- `time_1`: Start time for ORB checks (e.g., 09:16 AM).
- `time_2`: End time for volume-based re-entries (e.g., 03:15 PM).

## Trading Logic

### Opening Range Breakout (ORB)

1. The ORB strategy checks the high and low of the first minute candle after the market opens.
2. If a breakout occurs (high/low is broken by subsequent candles), a trade is initiated.
3. Buy if the breakout is above the high, or sell if the breakout is below the low.

### Volume-Based Entries

1. After the initial ORB trade, the script continuously monitors the volume.
2. If a candle's volume exceeds a certain factor (2.5x, 3x, or 3.5x of the 10-candle EMA), it becomes a candidate for re-entry.
3. The script waits for the next candle to confirm the breakout by breaking the high or low of the volume spike candle.

### Trailing Stop-Loss

- For ORB trades, the stop-loss is initially set and trails as the price moves in the favorable direction.
- The trailing stop-loss is adjusted based on a predefined factor for volume-based entries.

Here’s the updated document with the added adjustments and changes paragraph:

---
## Phase 2 Changes

### Volume Spike Criteria
- A volume spike is identified when the volume is greater than the EMA of the previous 10 candles multiplied by a factor of 2.5.
- Upon detecting a volume spike, the system checks the next candle. If the next candle breaks the high of the volume spike candle, a Call Buy is executed; if it breaks the low, a Put Buy is executed.

### Exit Strategy
- **Target:** A 30-point target is set upon entering a trade.
- **Stop-Loss:** A 15-point stop-loss is also set at the time of the trade.
- **Trailing Stop-Loss:** 
  - **Previous Logic:** The stop-loss was initially moved to the entry cost after gaining 15 points. For every additional 5 points of gain, the stop-loss would trail by 5 points.
  - **Updated Logic:** Now, the trailing stop-loss is adjusted only when a 2.5x volume spike is detected, with the stop-loss trailing directly by 5 points. The stop-loss does not move to the entry cost first.
- **Auto Square-Off:** If a position is not exited after 20 candles, the system will automatically square off the position.

### Adjustments and Changes
1. **Trailing Stop-Loss Adjustment:**
   - The trailing stop-loss is now only adjusted when a 2.5x volume spike is detected. The stop-loss will trail directly by 5 points, bypassing the previous logic of moving to the entry cost first.

2. **Auto Square-Off after 20 Candles:**
   - After executing a Buy or Sell position, if the position has not been exited after 20 candles, the system will automatically square off the position.

3. **Change in Terminology from Futures to Options:**
   - "Future Buy" has been replaced with "Call Buy."
   - "Future Sell" has been replaced with "Put Buy."

## Logging Trades

- Trades are logged into a CSV file with the following details:
  - Date
  - Entry Time
  - Entry Price
  - Trade Direction (BUY/SELL)
  - Exit Price
  - Exit Time
  - Exit Reason (Target Hit, Stop-loss Hit, Market Close)
  - P&L

### Example Code Snippet

```python
def log_trade_to_csv(today, entry_time, entry_price, direction, exit_price, exit_time, exit_reason, pnl):
    with open(log_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([today, entry_time, entry_price, direction, exit_price, exit_time, exit_reason, pnl])
```

## Execution

1. **Run the script:**

   ```bash
   python futures_1min_ORB_Live.py
   ```

2. **Monitor Logs:**
   - Logs are created to track the progress of the trading strategy, including decisions made, trades executed, and stop-loss adjustments.

3. **Review Trade Logs:**
   - After execution, review the `log_file` CSV to analyze the performance and decisions of the strategy.

## License

This project is licensed under the MIT License.

---

This README provides a clear understanding of the script's functionality and how to configure and execute it. Adjust paths, parameters, and any other configurations according to your specific requirements.
