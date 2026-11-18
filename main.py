"""Dip-buy bot for agent-fun/bars-replay/v1 (make.fun btc-race-24h-20261118-1444).

Strategy, in one line: buy cbBTC only after a deep dislocation has stopped
falling, ride the snap-back, and never chase a rally.

The hello message gives the universe (one symbol, CBBTC), the capital
(1,000 USDC), the caps (long only, one open position, 16 orders per bar) and
the fees (4 bps fee, 2 bps slippage, plus constant-product impact against the
bar's pool depth). Each batch carries one 1-minute bar and the account; every
reply answers exactly one batch with its orders, echoing its seq. An order
decided on the batch of the bar that closes at minute t fills at the open of
the next bar, so every decision here uses only closes already seen.

Why this shape: on this pool the 1-minute noise is tiny (about 7 bps) while a
full-size round trip costs about 26 bps in fee, slippage and impact, so a
trade must catch a real dislocation. The kit's high-frequency baselines
(EMA-cross, RSI-Bollinger) churn 70-80 trades on the dev window and lose
$120-148; a bot that trades twice and catches the one real swing wins.
A dip of 170 bps below the 60-bar mean is rare and it snaps back; buying it
while it is still falling is buying the knife, so the bot only buys on a
rising close (the dip has stopped falling). The exit is a 250 bps
take-profit, a 100 bps stop-loss, or a 480-bar max hold.

Two more layers, for windows without a deep dip:
- Secondary mode, after the first trade and between bars 300-1200: a
  shallower dip (90 bps below the 30-bar mean, also on a rising close),
  with a smaller take-profit (120 bps), stop-loss (60 bps) and max hold
  (240 bars). It never fires on the dev window; it exists so a quieter
  race window still gets traded.
- Late-window fallbacks (only if the bot has never traded at all): from
  bar 1200 a 40 bps dip is enough, from bar 1350 any 25 bps dip, and from
  bar 1380 a clear uptrend is enough -- if the window rose smoothly for 23
  hours with no dip at all, buying the trend for the last hour beats
  sitting out, and the race needs at least one trade.

Risk controls: at most one open position; a 30-bar cooldown after every
exit so one bad read cannot re-enter at once; the hold time is counted from
the first batch on which the position is actually held, not from the batch
the buy was sent on, so a fill that lands a bar later cannot shorten it.
No randomness, no clock, no network, no files: two executions on the same
bars produce the same orders.

Dev-window result (frozen 24h, 1,440 bars, graded locally with the kit's
own fill model): net PnL +$24.46 (+2.45%), max drawdown 1.50%, 2 trades,
fees $0.81. Buy-and-hold on the same window: -$31.63.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# --- tuned parameters (grid-searched on the frozen dev window, then
# stress-tested on scaled / block-shuffled / reversed / shifted copies of
# it and on the previous race's dev window) ---
SMA_BARS = 60            # mean window for the primary dip, in bars
DIP_BPS = 170            # buy when close is this far below the mean, in bps
TAKE_PROFIT_BPS = 250    # sell when close is this far above the entry price
STOP_LOSS_BPS = 100      # sell when close is this far below the entry price
MAX_HOLD_BARS = 480      # sell when the position is this old, whatever the price
COOLDOWN_BARS = 30       # bars to wait after any exit
SMA2_BARS = 30           # mean window for the secondary mode, in bars
DIP2_BPS = 90            # secondary dip threshold, in bps
TAKE_PROFIT2_BPS = 120   # secondary take-profit, in bps
STOP_LOSS2_BPS = 60      # secondary stop-loss, in bps
MAX_HOLD2_BARS = 240     # secondary max hold, in bars
SEC_FROM_BAR = 300       # secondary mode active from this bar
SEC_TO_BAR = 1200        # secondary mode active until this bar
MAX_SLIPPAGE_BPS = 300   # widest fill we accept, measured from the latest close
FALLBACK_BAR = 1200      # from here, accept a shallower dip if never traded
FALLBACK_DIP_BPS = 40
LAST_RESORT_BAR = 1350   # from here, accept any small dip if never traded
LAST_RESORT_DIP_BPS = 25
TREND_BAR = 1380         # from here, accept a clear uptrend if never traded
TREND_BPS = 50

BPS = 10_000


class Bot:
    """Keeps the bar history and the trade state across batches."""

    def __init__(self):
        self.closes = []
        self.entry_seq = -1
        self.cool_until = -1
        self.ever_traded = False
        self.mode = 1

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        close = state.close(SYMBOL)
        if close is None:
            return []
        self.closes.append(close)
        holding = state.positions.get(SYMBOL)
        qty = holding.qty if holding is not None else 0
        if qty > 0:
            self.ever_traded = True
            if self.entry_seq < 0:
                self.entry_seq = state.seq
            # Average entry price from the position's cost (fees included, so
            # this is a touch above the fill price: conservative both ways).
            entry_px = holding.cost * 10 ** 13 // (qty * 10 ** 6)
            move_bps = (close - entry_px) * BPS // entry_px
            if self.mode == 1:
                tp, sl, hold = TAKE_PROFIT_BPS, STOP_LOSS_BPS, MAX_HOLD_BARS
            else:
                tp, sl, hold = TAKE_PROFIT2_BPS, STOP_LOSS2_BPS, MAX_HOLD2_BARS
            if (
                move_bps >= tp
                or move_bps <= -sl
                or state.seq - self.entry_seq >= hold
            ):
                self.cool_until = state.seq + COOLDOWN_BARS
                self.entry_seq = -1
                return [
                    {
                        "side": "sell",
                        "symbol": SYMBOL,
                        "qty": qty,
                        "max_slippage_bps": MAX_SLIPPAGE_BPS,
                    }
                ]
            return []

        if state.seq < self.cool_until:
            return []
        if len(self.closes) < SMA_BARS:
            return []
        mean = sum(self.closes[-SMA_BARS:]) // SMA_BARS
        seq = state.seq
        dip_bps = (close - mean) * BPS // mean
        rising = close >= self.closes[-2]
        buy = False
        if dip_bps <= -DIP_BPS and rising:
            buy = True
            self.mode = 1
        elif self.ever_traded and SEC_FROM_BAR <= seq <= SEC_TO_BAR:
            mean2 = sum(self.closes[-SMA2_BARS:]) // SMA2_BARS
            dip2_bps = (close - mean2) * BPS // mean2
            if dip2_bps <= -DIP2_BPS and rising:
                buy = True
                self.mode = 2
        if not buy and not self.ever_traded:
            if seq >= TREND_BAR and dip_bps >= TREND_BPS:
                buy = True
            elif seq >= LAST_RESORT_BAR and dip_bps <= -LAST_RESORT_DIP_BPS:
                buy = True
            elif seq >= FALLBACK_BAR and dip_bps <= -FALLBACK_DIP_BPS:
                buy = True
            if buy:
                self.mode = 2
        if buy and state.cash > 0:
            return [
                {
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }
            ]
        return []


_BOT = Bot()


def on_batch(state, batch):
    return _BOT.on_batch(state, batch)


makefun_bars.run(on_batch)
