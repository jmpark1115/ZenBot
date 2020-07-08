# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

import sys
from configparser import ConfigParser
import logging
import math

from deadline import isDeadline
from foblgate import Foblgate
try:
    from config import ps
except :
    raise ValueError

gui_form = uic.loadUiType('zenBot.ui')[0]

def get_logger():
    logger = logging.getLogger("ZenBot")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()

    fh = logging.FileHandler('user.log', mode='a', encoding=None, delay=False)
    fh.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    formatter_fh = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    fh.setFormatter(formatter_fh)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = get_logger()


def print_ps():
    attrs = vars(ps)
    _ps = ', '.join("%s: %s" % item for item in attrs.items())
    logger.debug(_ps)
    return _ps

class Worker(QThread):

    update_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # Load Config File
        config = ConfigParser()
        config.read('trading_foblgate.conf')

        connect_key = config.get('XenBot', 'connect_key')
        secret_key = config.get('XenBot', 'secret_key')

        self.target  = 'XEN'
        self.payment = 'KRW'
        self.dryrun = int(config.get('XenBot', 'dryrun'))
        self.tick_interval = float(config.get('Param', 'tick_interval'))

        if connect_key and secret_key and self.tick_interval and self.target and self.payment:
            logger.debug("configurations ok")
        else:
            logger.debug("Please add info into configurations")
            raise ValueError

        self.bot = Foblgate(connect_key, secret_key, self.target, self.payment)

        self.result = {}

        self.runtime = 0  # 실행 시간 측정
        self.qty  = 0


    def set_run(self, price, qty, tot_run, mode):
        self.price = price
        self.qty  = qty
        self.tot_run = tot_run
        self.mode = mode

    def run(self):

        while True:
            if ps.run_flag:
               self.result = {}
               ret = self.bot.self_trading(ps)
               # ret = self.bot.api_test(ps)
               if ret:
                    self.update_signal.emit(ret)
               # return # one time do

            self.msleep(1000)


    def seek_balance(self):
        try:
            self.bot.Balance()
            return self.bot.targetBalance, self.bot.baseBalance
        except Exception as ex:
            logger.debug("seek balance error %s" %ex)
            return 0, 0


    def seek_orderbook(self, coin):
        try:
            self.bot.get_order_info(coin)
            return self.bot.askprice, self.bot.bidprice, self.bot.askqty, self.bot.bidqty
        except Exception as ex:
            logger.debug("seek orderbook error %s" %ex)
            return 0, 0, 0, 0

    def seek_ticker(self, coin):
        try:
            self.bot.get_ticker_info(coin)
            return self.bot.ticker
        except Exception as ex:
            logger.debug("seek ticker error %s" % ex)
            return 0

    def seek_spread(self, bid, ask):
        if self.tick_interval == 0.0 :
            return ValueError
        tick_floor = 1/self.tick_interval
        mid_price = (bid + ask) / 2
        mid_price = math.floor(mid_price * tick_floor) / tick_floor  # 버림처리
        if bid < mid_price < ask:
            return mid_price
        else:
            return 0

    def seek_midprice(self):

        self.seek_orderbook(self.coin)
        mid_price = self.seek_spread(self.bot.bidprice, self.bot.askprice)
        if mid_price <= 0:
            logger.debug('No spread : bids_price {} < mid_price {} < asks_price {}'
                         .format(self.bot.bidprice, mid_price, self.bot.askprice))
            return "Wait"
        else:
            return mid_price

class MyWindow(QMainWindow, gui_form):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.result = []

        self.user_confirm = False
        self.tot_run = 0
        self.per_run = 5
        self.mode = ''

        self.worker = Worker()
        self.worker.update_signal.connect(self.display_result)
        self.worker.start()

        # Load Config File
        config = ConfigParser()
        config.read('trading_foblgate.conf')
        dryrun = int(config.get('XenBot', 'dryrun'))
        ps.dryrun = True if dryrun else False
        ps.fr_price = float(config.get('Param', 'fr_price'))
        ps.to_price = float(config.get('Param', 'to_price'))
        ps.fr_qty = int(config.get('Param', 'fr_qty'))
        ps.to_qty = int(config.get('Param', 'to_qty'))
        ps.fr_time = int(config.get('Param', 'fr_time'))
        ps.to_time = int(config.get('Param', 'to_time'))
        ps.fr_off = int(config.get('Param', 'fr_off'))
        ps.to_off = int(config.get('Param', 'to_off'))
        ps.mode   = config.get('Param', 'mode')
        ps.ex_min_qty = int(config.get('Param', 'ex_min_qty'))
        ps.tick_interval = float(config.get('Param', 'tick_interval'))
        ps.run_flag = 0

        logger.debug('parameters setup %s' %ps)

        self.target  = 'XEN'
        self.payment = 'KRW'

        self.title_Label.setText('XEN Bot')
        self.MyDialgo()

    @pyqtSlot(str)
    def display_result(self, data):
        logger.debug('===>display_result')

        try:
            self.textBrowser.append(data)
        except Exception as ex:
            logger.debug('display_result fail %s' %ex)

    def MyDialgo(self):

        self.fr_price_lineEdit.setText('{:.2f}' .format(ps.fr_price))
        self.to_price_lineEdit.setText('{:.2f}' .format(ps.to_price))
        self.fr_time_lineEdit.setText(str(ps.fr_time))
        self.to_time_lineEdit.setText(str(ps.to_time))
        self.fr_qty_lineEdit.setText(str(ps.fr_qty))
        self.to_qty_lineEdit.setText(str(ps.to_qty))
        self.fr_off_lineEdit.setText(str(ps.fr_off))
        self.to_off_lineEdit.setText(str(ps.to_off))
        if ps.mode == 'random':
            self.random_radioButton.setChecked(True)
        elif ps.mode =='sell':
            self.sell_radioButton.setChecked(True)
        else:
            self.buy_radioButton.setChecked(True)

        self.confirm_pushButton.clicked.connect(self.confirm_cmd)
        self.action_pushButton.clicked.connect(self.action_cmd)
        self.stop_pushButton.clicked.connect(self.stop_cmd)

        self.random_radioButton.clicked.connect(self.mode_cmd)
        self.sell_radioButton.clicked.connect(self.mode_cmd)
        self.buy_radioButton.clicked.connect(self.mode_cmd)

        self.title_Label.setText("XEN Bot")
        self.delete_pushButton.clicked.connect(self.delete_logs_cmd)

        self.textBrowser.append('시스템 OK!')

    def confirm_cmd(self):
        logger.debug('confirm cmd')
        self.user_confirm = False

        fr_price = self.fr_price_lineEdit.text()
        to_price = self.to_price_lineEdit.text()
        fr_qty   = self.fr_qty_lineEdit.text()
        to_qty   = self.to_qty_lineEdit.text()
        fr_time   = self.fr_time_lineEdit.text()
        to_time   = self.to_time_lineEdit.text()
        fr_off   = self.fr_off_lineEdit.text()
        to_off   = self.to_off_lineEdit.text()

        if fr_price == '' or fr_qty == '' or fr_time == '' or fr_off == '':
            print("Type in parameters")
            self.textBrowser.append( '입력값을 확인해 주세요')
            return "Error"

        try:
            fr_price = float(fr_price)
            to_price = float(to_price) if to_price else 0
            fr_qty   = float(fr_qty)
            to_qty   = float(to_qty) if to_qty else 0
            fr_time = float(fr_time)
            to_time = float(to_time) if to_time else 0
            fr_off = float(fr_off) if fr_off else 10
            to_off = float(to_off) if to_off else 90

        except Exception as ex:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if fr_price <= 0 or fr_qty <= 0 or fr_time <= 0 or fr_off < 0:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_price > 0 and fr_price >= to_price:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_qty > 0 and fr_qty >= to_qty:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_time > 0 and fr_time >= to_time:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_off > 0 and fr_off >= to_off:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if to_off > 100:
            self.textBrowser.append('입력값을 확인해 주세요')
            return "Error"

        if self.sell_radioButton.isChecked():
            mode = 'sell'
            print('sell')
        elif self.buy_radioButton.isChecked():
            mode = 'buy'
            print('buy')
        elif self.random_radioButton.isChecked():
            mode = 'random'
        else:
            mode = ''
            self.textBrowser.append('Mode를 선택해 주세요')
            return "Error"

        ps.fr_price = fr_price
        ps.to_price = to_price
        ps.fr_qty = fr_qty
        ps.to_qty = to_qty
        ps.fr_time = fr_time
        ps.to_time = to_time
        ps.fr_off = fr_off
        ps.to_off = to_off
        ps.mode   = mode
        ret = print_ps()
        self.textBrowser.append( "파라메타 설정 완료")
        self.textBrowser.append(ret)

        self.user_confirm = True  #입력 ok

        self.worker.bot.Orderbook()
        self.bestoffer_Label.setText("Ask {:5.0f}@{:.2f}\nBid {:5.0f}@{:.2f}"
                                     .format(self.worker.bot.asks_qty, self.worker.bot.asks_price
                                             ,self.worker.bot.bids_qty, self.worker.bot.bids_price))
        self.worker.bot.Balance()
        self.balance_Label.setText("{:.0f} {}\n{:.0f} {}"
                    .format(self.worker.bot.targetBalance, self.target,
                            self.worker.bot.baseBalance, self.payment))
        return

    # https://stackoverflow.com/questions/18925241/send-additional-variable-during-pyqt-pushbutton-click
    def action_cmd(self, state):
        logger.debug('action cmd')

        # check deadline
        '''
        check = isDeadline()
        if check == 'NG':
            self.textBrowser.append('사용기간이 만료되었습니다')
            return "Error"
        elif check == 'ERROR':
            self.textBrowser.append('네트워크를 점검해 주세요')
            return "Error"
        else:
            self.textBrowser.append('Bot Validation OK')
        '''
        # end check deadline

        if not self.user_confirm:  # 입력 ok ?
            self.textBrowser.append( '입력값을 확인해 주세요')
            return

        ps.run_flag = 1
        self.textBrowser.append( '실행합니다')
        return

    def stop_cmd(self):
        logger.debug('stop_cmd')

        ps.run_flag = 0
        self.textBrowser.append( '정지합니다')
        return

    def mode_cmd(self):
        if self.sell_radioButton.isChecked():
            mode = 'sell'
            print('sell')
        elif self.buy_radioButton.isChecked():
            mode = 'buy'
            print('buy')
        elif self.random_radioButton.isChecked():
            mode = 'random'
        else:
            mode = ''
            logger.debug('mode is invalid')
            return

        ps.mode = mode
        return

    def autoinput_cmd(self):
        val = self.worker.seek_midprice()
        if val == "Wait":
            self.price_lineEdit.setText("{}".format(val))
            self.textBrowser.append("Please wait. No spread")
        else:
            self.price_lineEdit.setText("{}" .format(val))

    def delete_logs_cmd(self):
        self.textBrowser.clear()


def main_QApp():
    app = QApplication(sys.argv)
    main_dialog = MyWindow()
    main_dialog.show()
    app.exec_()


if __name__ == '__main__':
    main_QApp()
