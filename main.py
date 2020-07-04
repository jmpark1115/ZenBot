# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

import sys
from configparser import ConfigParser
import logging
import timeit
import math
import time
import random

from deadline import isDeadline
from foblgate import Foblgate
try:
    from config import ps
except :
    raise ValueError

gui_form = uic.loadUiType('zenBot.ui')[0]

stop_flag = True
stop1_flag = True

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

class Worker(QThread):

    update_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # Load Config File
        config = ConfigParser()
        config.read('trading_foblgate.conf')

        connect_key = config.get('ZenBot', 'connect_key')
        secret_key = config.get('ZenBot', 'secret_key')

        self.target  = config.get('ZenBot', 'target')
        self.payment = config.get('ZenBot', 'payment')
        self.dryrun = int(config.get('ZenBot', 'dryrun'))
        self.tick_interval = float(config.get('ZenBot', 'tick_interval'))

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
            global stop_flag
            if stop_flag == False:
               # stop_flag = True
               self.result = {}
               ret = self.bot.self_trading(ps)
               # ret = self.bot.api_test(ps)
               if ret:
                    self.update_signal.emit(self.result)
               # return # one time do

            self.msleep(1000)


    def seek_balance(self, number):
        logger.debug('->execute function executing {}'.format(number))
        result = self.bot.balance('ETH')
        logger.debug('<-execute function ended with: {}'.format(number))
        return (result, 'ok')


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

        self.target = config.get('ZenBot', 'target')
        if self.target:
            self.title_Label.setText(self.target)
        else:
            self.textBrowser.append('Please add coin name in trading.conf file')
            raise ValueError

        self.MyDialgo()

    @pyqtSlot(dict)
    def display_result(self, data):
        logger.debug('===>display_result')

        try:
            message = ''
            message += data

            self.textBrowser.append(message)
            self.user_confirm = False

        except Exception as ex:
            logger.debug('display_result fail %s' %ex)

    def MyDialgo(self):

        self.confirm_pushButton.clicked.connect(self.confirm_cmd)
        self.action_pushButton.clicked.connect(self.action_cmd)

        self.random_radioButton.clicked.connect(self.mode_cmd)
        self.sell_radioButton.clicked.connect(self.mode_cmd)
        self.buy_radioButton.clicked.connect(self.mode_cmd)

        self.title_Label.setText("target : {}" .format(self.target))
        self.delete_pushButton.clicked.connect(self.delete_logs_cmd)

        self.stop_pushButton.setCheckable(True)
        self.stop_pushButton.clicked[bool].connect(self.stopme_cmd)

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

        if fr_price == '' or fr_qty == '' or fr_time == '' :
            print("Type in parameters")
            self.textBrowser.setText('메시지 : ' + '입력값을 확인해 주세요')
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
            self.textBrowser.setText('입력값을 확인해 주세요')
            return "Error"

        if fr_price <= 0 or fr_qty <= 0 or fr_time <= 0 or fr_off <= 0:
            self.textBrowser.setText('입력값을 확인해 주세요')
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
            self.textBrowser.setText('Mode를 선택해 주세요')
            return "Error"

        ps.fr_price = fr_price = 0.60
        ps.to_price = to_price = 0.70
        ps.fr_qty = fr_qty = 1000
        ps.to_qty = to_qty = 1010
        ps.fr_time = fr_time = 1
        ps.to_time = to_time = 10
        ps.fr_off = fr_off   = 10
        ps.to_off = to_off   = 90
        ps.mode   = mode     = 'random'
        ps.tick_interval = 0.01 #???
        # self.worker.set_run(ps)
        self.textBrowser.append("메시지 : " + "파라메타 설정 완료")
        return

    # https://stackoverflow.com/questions/18925241/send-additional-variable-during-pyqt-pushbutton-click
    def stopme_cmd(self, state):
        global stop1_flag

        source = self.sender()
        if state:
            print('계속 -> 정지')
            source.setText('PLAY')
            #     정지 동작
            result = '계속 -> 정지'
            stop1_flag = True
        else:
            print('정지 -> 계속')
            source.setText('STOP')
            # 계속 동작
            result = '정지 -> 계속'
            stop1_flag = False

        self.textBrowser.setText('메시지 : ' + str(result))

    def action_cmd(self):
        logger.debug('action cmd')
        # check deadline
        check = isDeadline()
        if check == 'NG':
            self.textBrowser.setText('사용기간이 만료되었습니다')
            return "Error"
        elif check == 'ERROR':
            self.textBrowser.setText('네트워크를 점검해 주세요')
            return "Error"
        else:
            self.textBrowser.setText('Bot Validation OK')
        # end check deadline

        # confirm for user input
        self.user_confirm = True

        self.textBrowser.append("do action")
        global stop_flag
        print('stop flag ' , stop_flag)
        stop_flag = False

    def refresh_cmd(self):
        askprice, bidprice, askqty, bidqty = self.worker.seek_orderbook(self.target)
        ticker = self.worker.seek_ticker(self.target)
        self.last_lineEdit.setText("{:.4f}".format(ticker))
        self.ask_lineEdit.setText("{:5.0f}@{:.4f}".format(askqty, askprice))
        self.bid_lineEdit.setText("{:5.0f}@{:.4f}".format(bidqty, bidprice))
        self.textBrowser.append("ASKS {:5.0f}@{:.4f}".format(askqty, askprice))
        self.textBrowser.append("BIDS {:5.0f}@{:.4f}".format(bidqty, bidprice))

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
