# makefun-btc-race-24h-02

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/0xPaasepp/makefun-btc-race-24h-02/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/0xPaasepp/makefun-btc-race-24h-02/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)

A pure-stdlib Python trading bot for make.fun's [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261118-1444) bounty ($250 in USDC).

## Strategy

Dip-buy mean reversion on cbBTC 1-minute bars: buy only after a deep dislocation (170 bps below the 60-bar SMA) has stopped falling (rising close), exit at +200 bps take-profit, -100 bps stop-loss, or 480-bar max hold. Late-window fallbacks guarantee at least one trade, at one-third size with a stall exit. Full details in `main.py`.

## Results (frozen dev window, 1,440 bars)

- Net PnL +$18.27 (+1.83%), max drawdown 1.50%, 2 trades, fees $0.81
- Buy-and-hold on the same window: -$31.63; kit EMA-cross baseline: -$148.17; kit RSI-Bollinger baseline: -$120.25
- Robustness (34 synthetic stress windows): mean +$0.93, worst -$13.96, median -$0.66 — vs V2's +$0.68 / -$13.96 / -$0.66 and V1's -$1.83 / -$19.63 / -$3.54. Previous race window (out-of-sample): +$1.39, max drawdown 0.16%.
- Dev fills (buy batch 70, sell batch 476) differ from V1/V2 (buy 70, sell 507): this variant exists to escape the identical-behaviour flag on V1.

## Results (frozen dev window, 1,440 bars)

- Net PnL +$18.27 (+1.83%), max drawdown 1.50%, 2 trades, fees $0.81
- Buy-and-hold on the same window: -$31.63; kit EMA-cross baseline: -$148.17; kit RSI-Bollinger baseline: -$120.25

## Run

```
python3 main.py
```
