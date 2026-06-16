import backtrader as bt
import pandas as pd
import numpy as np
import datetime
import os

def rq_weights(lookback, weight, window_size=50):
    w = np.zeros(window_size)
    for i in range(window_size):
        w[i] = (1 + (i**2) / (2 * weight * lookback**2)) ** (-weight)
    return w

class RQSupertrend(bt.Indicator):
    lines = ('supertrend', 'direction',)
    params = (
        ('factor', 3.0),
        ('atr_period', 10),
        ('kernel_lookback', 8),
        ('kernel_weight', 8),
        ('window_size', 50),
    )

    def __init__(self):
        self.atr = bt.indicators.ATR(self.data, period=self.p.atr_period)
        self.w = rq_weights(self.p.kernel_lookback, self.p.kernel_weight, self.p.window_size)
        self.addminperiod(max(self.p.window_size, self.p.atr_period))

    def next(self):
        if len(self) < self.p.window_size:
            return

        closes = self.data.close.get(size=self.p.window_size)
        highs = self.data.high.get(size=self.p.window_size)
        lows = self.data.low.get(size=self.p.window_size)

        smooth_close = np.sum(np.array(closes)[::-1] * self.w) / np.sum(self.w)
        smooth_high = np.sum(np.array(highs)[::-1] * self.w) / np.sum(self.w)
        smooth_low = np.sum(np.array(lows)[::-1] * self.w) / np.sum(self.w)

        hl2 = (smooth_high + smooth_low) / 2

        basic_upperband = hl2 + (self.p.factor * self.atr[0])
        basic_lowerband = hl2 - (self.p.factor * self.atr[0])

        if len(self) == self.p.window_size:
            self.lines.supertrend[0] = basic_upperband
            self.lines.direction[0] = 1
            return

        prev_supertrend = self.lines.supertrend[-1]
        prev_dir = self.lines.direction[-1]

        if prev_dir == 1:
            upperband = min(basic_upperband, prev_supertrend)
            if smooth_close > upperband:
                self.lines.supertrend[0] = basic_lowerband
                self.lines.direction[0] = -1
            else:
                self.lines.supertrend[0] = upperband
                self.lines.direction[0] = 1
        else:
            lowerband = max(basic_lowerband, prev_supertrend)
            if smooth_close < lowerband:
                self.lines.supertrend[0] = basic_upperband
                self.lines.direction[0] = 1
            else:
                self.lines.supertrend[0] = lowerband
                self.lines.direction[0] = -1

class MyStrategy(bt.Strategy):
    params = (
        ('stop_loss_atr_factor', 2.5),
        ('printlog', True),
    )

    def log(self, txt, dt=None):
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.rqst = RQSupertrend(self.data)
        self.consecutive_bullish = 0
        self.consecutive_bearish = 0

        self.order = None
        self.sl_order = None

        self.last_signal_dir = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f' % order.executed.price)
            else:
                self.log('SELL EXECUTED, Price: %.2f' % order.executed.price)

            if order == self.order:
                self.order = None
            elif order == self.sl_order:
                self.log('STOP LOSS TRIGGERED')
                self.sl_order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected: %s' % order.status)
            if order == self.order:
                self.order = None
            elif order == self.sl_order:
                self.sl_order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' % (trade.pnl, trade.pnlcomm))

    def next(self):
        if pd.isna(self.rqst.direction[0]):
            return

        current_dir = self.rqst.direction[0]

        if current_dir == -1:
            self.consecutive_bullish += 1
            self.consecutive_bearish = 0
        elif current_dir == 1:
            self.consecutive_bearish += 1
            self.consecutive_bullish = 0

        confirmed_dir = None
        if self.consecutive_bullish >= 2:
            confirmed_dir = -1
        elif self.consecutive_bearish >= 2:
            confirmed_dir = 1

        if confirmed_dir is None:
            return

        if self.order:
            return

        flip_to_bullish = (confirmed_dir == -1) and (self.last_signal_dir != -1)
        flip_to_bearish = (confirmed_dir == 1) and (self.last_signal_dir != 1)

        if flip_to_bullish:
            self.last_signal_dir = -1
            if self.sl_order:
                self.cancel(self.sl_order)
                self.sl_order = None

            trade_size = 1 - self.position.size
            if trade_size > 0:
                self.order = self.buy(size=trade_size)
                sl_price = self.data.close[0] - self.p.stop_loss_atr_factor * self.rqst.atr[0]
                self.sl_order = self.sell(size=1, exectype=bt.Order.Stop, price=sl_price)

        elif flip_to_bearish:
            self.last_signal_dir = 1
            if self.sl_order:
                self.cancel(self.sl_order)
                self.sl_order = None

            trade_size = self.position.size - (-1)
            if trade_size > 0:
                self.order = self.sell(size=trade_size)
                sl_price = self.data.close[0] + self.p.stop_loss_atr_factor * self.rqst.atr[0]
                self.sl_order = self.buy(size=1, exectype=bt.Order.Stop, price=sl_price)

if __name__ == '__main__':
    if not os.path.exists('raw/nifty.csv'):
        import yfinance as yf
        if not os.path.exists('raw'):
            os.makedirs('raw')
        df = yf.download('^NSEI', start='2022-01-01', end='2024-01-01')
        df.to_csv('raw/nifty.csv')

    df = pd.read_csv('raw/nifty.csv', header=[0,1], index_col=0, parse_dates=True)
    df.columns = [col[0].lower() for col in df.columns]
    df.index.name = 'date'

    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.broker.setcash(100000.0)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
