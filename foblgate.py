import time
import hashlib
from operator import itemgetter
import hmac
import requests

import logging
logger = logging.getLogger(__name__)

# https://api-document.foblgate.com/
API_URL = 'https://api2.foblgate.com'
# API_URL = 'https://qao-qao-api2.foblgate.com'

# coding=utf-8
import time
import random
import math
from decimal import Decimal as D
from decimal import getcontext


class Common(object):

    def __init__(self, api_key, api_secret, target, payment):
        self.connect_key = api_key
        self.secret_key = api_secret
        self.target = target
        self.payment = payment
        self.targetBalance = 0
        self.baseBalance = 0
        self.bids_qty = 0
        self.bids_price = 0
        self.asks_qty = 0
        self.asks_price = 0

        bot_conf = None
        # self.get_config()
        self.GET_TIME_OUT = 30
        self.POST_TIME_OUT = 60

        self.mid_price = 0 # previous mid_price

        self.nickname = 'foblgate'
        self.symbol = '%s/%s' %(self.target, self.payment)

    def get_config(self):
        logger.debug('get_config')
        try:
            # bot_conf = AutoBot.objects.get(id=self.id)
            pass
        except Exception as ex:
            logger.debug('db configuration error %s' % ex)

    def save_mid_price(self, mid_price, bot_conf):
        try:
            bot_conf.mid_price = mid_price
        except Exception as ex:
            logger.debug('save mid_price error %s' % ex)
        return

    def get_mid_price(self, bot_conf):
        try:
            return bot_conf.mid_price
        except Exception as ex:
            logger.debug('get mid_price error %s' % ex)
            return 0

    def seek_spread(self, bid, ask, bot_conf):
        sp = list()
        sum = 0.0
        i = 1
        getcontext().prec = 10
        tick_interval = bot_conf.tick_interval
        tick_floor = float(D(1) / D(tick_interval))
        while True:
            sum = float(D(bid) + D(i) * D(tick_interval))
            if bid < sum < ask:
                result = math.floor(sum * tick_floor) / tick_floor
                if result != bid:
                    sp.append(result)
                i += 1
            else:
                break
        size = len(sp)
        from_off = int(size * bot_conf.fr_off * 0.01)
        to_off = int(size * bot_conf.to_off * 0.01)
        if not to_off: to_off = 1
        logger.debug('from_off {} to_off {}' .format(from_off, to_off) )
        sp = sp[from_off:to_off]
        size = len(sp)
        # Avoid same price
        if self.mid_price in sp and size > 1:
            sp.remove(self.mid_price)
        if size:
            random.shuffle(sp)
            return sp.pop()

        return 0

    def seek_trading_info(self, asks_qty, asks_price, bids_qty, bids_price, bot_conf):

        # seek mid price
        mid_price = self.seek_spread(bids_price, asks_price, bot_conf)
        if mid_price <= 0:
            logger.debug('No spread in {} : bids_price {} < mid_price {} < asks_price {}'
                         .format(self.nickname, bids_price, mid_price, asks_price))
            return 0, 0
        # seek end
        if bot_conf.to_price:
            if bot_conf.fr_price < mid_price < bot_conf.to_price:
                price = mid_price
            else:
                logger.debug('#1 out of price range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_price, mid_price,
                                                                        bot_conf.to_price))
                return 0, 0
        else:
            if bot_conf.fr_price < mid_price:
                price = mid_price
            else:
                logger.debug('#2 out of price range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_price, mid_price,
                                                                 bot_conf.to_price))
                return 0, 0

        max_qty = int(min(self.targetBalance, int(self.baseBalance / price)))

        TradeSize = 0
        if bot_conf.to_qty:
            if bot_conf.to_qty < max_qty:
                TradeSize = random.randrange(bot_conf.fr_qty, bot_conf.to_qty)
            elif bot_conf.fr_qty < max_qty < bot_conf.to_qty:
                TradeSize = random.randrange(bot_conf.fr_qty, max_qty)
            else:
                logger.debug('Trade out of range in {} {} < {} <{}'.format(self.nickname, bot_conf.fr_qty, max_qty,
                                                                                 bot_conf.to_qty))
                return 0, 0
        else:
            if bot_conf.fr_qty < max_qty:
                TradeSize = bot_conf.fr_qty
            else:
                logger.debug('Trade lower in {} target: {} payment: {}'.format(self.nickname, self.targetBalance, self.baseBalance))
                return 0, 0

        if bot_conf.ex_min_qty:
            if TradeSize < bot_conf.ex_min_qty:
                TradeSize = 0
                logger.debug('Trade size is lower than exchanger min_qty requirement')

        return TradeSize, price

    def job_function(self):
        print("ticker", "| [time] "
              , str(time.localtime().tm_hour) + ":"
              + str(time.localtime().tm_min) + ":"
              + str(time.localtime().tm_sec))

    # def order_update(self, order_id, tran):
    def order_update(self, order_id, qty, side):

        # first try update
        logger.debug('order_update order_id : {}' .format(order_id))
        if order_id == 0 or order_id == '':
            logger.error('order_update id is invalid')
            return
        try:
            status, units_traded, avg_price, fee = self.review_order(order_id, qty, side)
            if units_traded != qty:
                # tran.mark = True
                self.Cancel(order_id)
            # tran.avg_price   = avg_price
            # tran.fee         = fee
            # tran.save()
        except Exception as ex:
            logger.debug('order_update exception %s' %ex)

    def api_test(self, bot_conf):

        result = self.Orderbook()
        if result == False:
            logger.debug('Orderbook Error at {}' .format(self.nickname))
            return
        print("ASKS {:5.0f}@{:.4f} at {}".format(self.asks_qty, self.asks_price, self.nickname))
        print("BIDS {:5.0f}@{:.4f} at {}".format(self.bids_qty, self.bids_price, self.nickname))
        mid_price = self.seek_spread(self.bids_price, self.asks_price, bot_conf)
        # price = mid_price
        price = mid_price
        qty   = 1000
        status, order_id, content = self.Order(price, qty, 'SELL')
        print("1", status, order_id, content)
        status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
        # status, order_id2, content = self.Order(price, qty, 'BUY')
        # print("2", status, order_id2, content)
        # status, units_traded, avg_price, fee = self.review_order(order_id2, qty)
        # print('SEL status : {} units_traded : {}/{} at {} {}'
        #       .format(status, units_traded, qty, self.name,self.symbol))
        if not order_id:
            return

        self.Cancel(order_id, price, 'SELL')
        status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
        print('SEL status : {} units_traded : {}/{} at {} {}'
              .format(status, units_traded, qty, self.nickname,self.symbol))

    def self_trading(self, bot_conf):

        logger.debug('-- self_trading with {} {}' .format(self.nickname, self.symbol))
        msg = ''
        if bot_conf.to_time and bot_conf.fr_time < bot_conf.to_time:
            mother = random.randrange(bot_conf.fr_time, bot_conf.to_time)
        else:
            mother = bot_conf.fr_time
            if mother < 10:
                mother = 10

        logger.debug('{} {} Time {}'.format(self.nickname, self.symbol, mother))
        time.sleep(mother)

        self.mid_price = bot_conf.mid_price #self.get_mid_price()
        logger.debug('previous mid price {}' .format(self.mid_price))

        self.Balance()
        before_m = 'Before: target {} - base {}'.format(self.targetBalance, self.baseBalance)

        start = time.time()
        logger.debug('--> Trading Start {} {}' .format(self.nickname, self.symbol))
        result = self.Orderbook()
        if result == False:
            logger.debug('Orderbook Error at {}' .format(self.nickname, self.symbol))
            return

        text = "ASKS {:5.0f}@{:.8f} at {} {}\n".format(self.asks_qty, self.asks_price, self.nickname, self.symbol)
        msg += text
        logger.debug(text)
        text = "BIDS {:5.0f}@{:.8f} at {} {}\n".format(self.bids_qty, self.bids_price, self.nickname, self.symbol)
        msg += text
        logger.debug(text)


        qty, price = self.seek_trading_info(self.asks_qty, self.asks_price,
                                            self.bids_qty, self.bids_price, bot_conf)

        if qty <= 0 or price <= 0:
            text = 'This is not trading situation. {} {}\n'.format(self.nickname, self.symbol)
            msg += text
            logger.debug('This is not trading situation {} {}' .format(self.nickname, self.symbol))
            return

        if bot_conf.mode == 'random':
            if random.randint(0, 1) == 0:
                mode = 'sell2buy'
            else:
                mode = 'buy2sell'
        else:
            mode = bot_conf.mode

        text = '{}@{}-{}/{} at {}{}\n'.format(qty, price, mode, bot_conf.mode, self.nickname, self.symbol)
        msg += text
        logger.debug(text)

        prev_order_id = 0

        if mode == 'sell2buy' or mode == 'sell':
            if bot_conf.dryrun == False:
                try:
                    status, order_id, content = self.Order(price, qty, 'SELL')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to sell %s' % content)
                        return
                except Exception as ex:
                    logger.error('fail to order')
                    return

                time.sleep(0.01)
                #
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
                text = 'SEL status : {} units_traded : {}/{} at {} {} with {}\n' .format(status, units_traded, qty, self.nickname, self.symbol, order_id)
                msg += text
                logger.debug(text)
                args = ''

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'sell',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 1, False, self.bids_price, self.asks_price)
                    # first = self.DB_WRITE(args)
                    first_qty  = qty
                    first_side = 'SELL'
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return
                if status == "SKIP":  # filled or cancelled
                    # first.mark = True
                    # first.save()
                    return
                elif status == "NG":  # partially filled
                    qty -= units_traded
                    if bot_conf.ex_min_qty > qty:
                        # first.mark = True
                        # first.save()
                        text = 'qty {} is lower than min_qty {}'.format(qty, bot_conf.ex_min_qty)
                        msg+= text
                        logger.debug(text)
                        self.Cancel(order_id)
                        return
                    else:
                        prev_order_id = order_id
                else:  # GO, unfilled
                    prev_order_id = order_id
                #
                try:
                    status, order_id, content = self.Order(price, qty, 'BUY')
                    if status is not 'OK' or order_id == 0 or order_id == '':
                        logger.debug('fail to buy %s' % content)
                        # first.mark = True
                        # first.save()
                        self.Cancel(prev_order_id, first_qty, first_side)
                        return
                except Exception as ex:
                    logger.error('fail to order %s' %ex)
                    # first.mark = True
                    # first.save()
                    self.Cancel(prev_order_id, first_qty, first_side)
                    return

                time.sleep(1)
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'BUY')
                text = 'BUY status : {} units_traded : {}/{} at {} {} with {}\n'.format(status, units_traded, qty, self.nickname,
                                                                               self.symbol, order_id)
                msg += text
                logger.debug(text)
                args = ''

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'buy',
                    #     units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #     self.baseBalance, order_id, 2, False, self.bids_price, self.asks_price)
                    # second = self.DB_WRITE(args)
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled, normal process
                    self.order_update(prev_order_id, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    pass
                elif status == "NG":  # partially filled
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_qty, first_side)
                    qty -= units_traded
                    logger.debug('partially filled, cancel pending order {}'.format(qty))
                    self.Cancel(order_id, qty, 'BUY')
                    self.save_mid_price(price, bot_conf)
                    return
                else: # GO
                    logger.debug('unfilled, cancel pending order')
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_qty, first_side)
                    self.Cancel(order_id, qty, 'BUY')
                    self.save_mid_price(price, bot_conf)
                    return
            else:
                logger.debug('skip sell2buy in drymode')

        elif mode == 'buy2sell' or mode == 'buy':
            if bot_conf.dryrun == False:

                try:
                    status, order_id, content = self.Order(price, qty, 'BUY')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to buy %s' % content)
                        return
                except Exception as ex:
                    logger.error('fail to order')
                    return

                time.sleep(0.1)
                #
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'BUY')
                text = 'BUY status : {} units_traded : {}/{} at {} with {}\n'.format(status, units_traded, qty, self.nickname, self.symbol, order_id)
                msg += text
                logger.debug(text)
                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'buy',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 1, False, self.bids_price, self.asks_price)
                    # first = self.DB_WRITE(args)
                    first_qty  = qty
                    first_side = 'BUY'
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled or cancelled
                    # first.mark = True
                    # first.save()
                    return
                elif status == "NG":  # partially filled
                    qty -= units_traded
                    if bot_conf.ex_min_qty > qty:
                        # first.mark = True
                        # first.save()
                        logger.debug('qty {} is lower than min_qty {}'.format(qty, bot_conf.ex_min_qty))
                        self.Cancel(order_id, qty, 'BUY')
                        return
                    else:
                        prev_order_id = order_id
                else:  # GO, unfilled
                    prev_order_id = order_id
                    pass
                #
                try:
                    status, order_id, content = self.Order(price, qty, 'SELL')
                    if status is not 'OK' or order_id == 0 or order_id == '' :
                        logger.debug('fail to sell %s' % content)
                        # first.mark = True
                        # first.save()
                        self.Cancel(prev_order_id, first_qty , first_side)
                        return
                except Exception as ex:
                    logger.error('fail to order %s' % content)
                    # first.mark = True
                    # first.save()
                    self.Cancel(prev_order_id, first_qty , first_side)
                    return

                time.sleep(1)
                status, units_traded, avg_price, fee = self.review_order(order_id, qty, 'SELL')
                text = 'SEL status : {} units_traded : {}/{} at {} {} with {}\n'.format(status, units_traded, qty, self.nickname,
                                                                               self.symbol, order_id)
                msg += text
                logger.debug(text)

                try:
                    pass
                    # args = (bot_conf.user.username, bot_conf.name, bot_conf.exchanger, 'sell',
                    #         units_traded, qty, avg_price, price, fee, bot_conf.mode, status, self.targetBalance,
                    #         self.baseBalance, order_id, 2, False, self.bids_price, self.asks_price)
                    # second = self.DB_WRITE(args)
                except Exception as ex:
                    logger.error("db exception %s / %s" %(ex, args))
                    return

                if status == "SKIP":  # filled
                    self.order_update(prev_order_id, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    pass
                elif status == "NG":  # partially filled
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_qty, first_side)
                    qty -= units_traded
                    logger.debug('partially filled, cancel pending order {}'.format(qty))
                    self.Cancel(order_id, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    return
                else: # GO
                    logger.debug('unfilled, cancel pending order')
                    # second.mark = True
                    # second.save()
                    self.order_update(prev_order_id, first_qty, first_side)
                    self.Cancel(order_id, first_qty, first_side)
                    self.save_mid_price(price, bot_conf)
                    return
        else:
            logger.debug('Invalid mode')

        logger.debug('<-- Trading End {} {} elapsed time {:.2f}\n' .format(self.nickname, self.symbol, time.time()-start))
        # self.Balance()
        return msg

    def DB_WRITE(self, args):
        return 'OK'

class Foblgate(Common):

    def __init__(self, api_key, api_secret, target, payment):
        super().__init__(api_key, api_secret, target, payment)

        self.id = id
        self.mbid = 'hge4014@naver.com'
        # self.mbid = 'icofrees@gmail.com'
        # self.mbid = 'zerobizcoin@naver.com'
        self.mid_price = 0 # previous mid_price

    def http_request(self, method, path, params=None, headers=None, auth=None):
        url = API_URL + path
        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=self.GET_TIME_OUT)
                if response.status_code == 200:
                    response = response.json()
                    return response
                else:
                    logger.error('http_request_{}_{}_{}_{}'.format(method, url, params, response.read()))
            if method == "POST":
                response = requests.post(url, data=params, headers=headers, timeout=self.POST_TIME_OUT)
                if response.status_code == 200:
                    response = response.json()
                    return response
                else:
                    logger.error('http_request_{}_{}_{}_{}'.format(method, url, params, response.read()))
        except Exception as e:
            logger.error('http_request_{}_{}_{}'.format(url, params, e))

        return False

    def _produce_sign(self, params):
        sign_str = ''
        sign_str += self.connect_key
        for k in params.values():
            sign_str += "{}" .format(k)
        sign_str += self.secret_key
        params['apiKey'] = self.connect_key
        md5 = hashlib.sha256()
        md5.update(sign_str.encode())
        sign = md5.hexdigest()
        return sign

    def ticker(self, symbol):
        path =  '/open/api/get_ticker'
        request = {
            'symbol': symbol
        }
        res =   self.http_request('GET', path, request)
        if res is False:
            return False

        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    a = float(res['data']['buy'])
                    b = float(res['data']['sell'])
                    return (a, b)

    def depth_all(self, symbol):
        path =  '/open/api/market_dept'
        request = {
            'symbol': symbol,  # 币种对
            'type': 'step0'  # 深度类型,step0, step1, step2（合并深度0-2）；step0时，精度最高
        }
        res =   self.http_request('GET', path, request)
        if not res:
            return False

        buy_list = []
        sell_list = []
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'tick' in res['data']:
                        if res['data']['tick']:
                            if 'bids' in res['data']['tick']:
                                for i in res['data']['tick']['bids']:
                                    price = float(i[0])
                                    amount = float(i[1])
                                    buy_list.append([price, amount])
                            if 'asks' in res['data']['tick']:
                                for i in res['data']['tick']['asks']:
                                    price = float(i[0])
                                    amount = float(i[1])
                                    sell_list.append([price, amount])
        buy_list = sorted(buy_list, key=itemgetter(0), reverse=True)  # data["data"]["tick"]["bids"]
        sell_list = sorted(sell_list, key=itemgetter(0))  # data["data"]["tick"]["asks"]
        return {'bids': buy_list, 'asks': sell_list}

    def depth_my(self, symbol):
        path =  '/exchange-open-api/open/api/v2/new_order'
        request = {
            "pageSize": 200,
            "symbol": symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('GET', path, request)
        if not res:
            return False

        buy_list = []
        sell_list = []
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'resultList' in res['data']:
                        if res['data']['resultList']:
                            for i in res['data']['resultList']:
                                price = float(i["price"])
                                amount = float(i["volume"])
                                order_id = i["id"]
                                if i['side'] == "BUY":
                                    buy_list.append((price, order_id, amount))
                                if i['side'] == "SELL":
                                    sell_list.append((price, order_id, amount))
        buy_list = sorted(buy_list, key=itemgetter(0), reverse=True)  # data["data"]["tick"]["bids"]
        sell_list = sorted(sell_list, key=itemgetter(0))  # data["data"]["tick"]["asks"]
        return {'bids': buy_list, 'asks': sell_list}

    def balances(self):
        path =  '/open/api/user/account'
        request = {}
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('GET', path, request)
        if not res:
            return False
        bal = {}
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'coin_list' in res['data']:
                        if res['data']['coin_list']:
                            for i in res['data']['coin_list']:
                                free = float(i["normal"])
                                freeze = float(i["locked"])
                                coin = i["coin"]
                                if free + freeze > 0.0:
                                    bal[coin] = {"free": free, "freeze": freeze}
        return bal

    def create_order(self, symbol, price, amount, side):
        path =  '/open/api/create_order'
        request = {
            "side": side.upper(),  # buy or sell
            "type": 1,  # 挂单类型:1.限价委托2.市价委托
            "volume": amount,  # type=1买卖数量 type=2买总价格，卖总个数
            "price": price,  # type=1委托单价
            "symbol": symbol,  # 市场标记
            "fee_is_user_exchange_coin": 0
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('POST', path, request)
        if res['code'] == 0:
            print('order', symbol, price, amount, side, res['code'])
        else:
            print('order', symbol, price, amount, side, res)

    def cancel_order(self, symbol, order_id):
        path =  '/open/api/cancel_order'
        request = {
            "order_id": order_id,
            "symbol": symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('POST', path, request)
        if res['code'] == 0:
            print('order', symbol, order_id, res['code'])
        else:
            print('order', symbol, order_id, res)

    def Ticker(self):
        path =  '/open/api/get_ticker'
        request = {
            'symbol': self.symbol
        }
        res =   self.http_request('GET', path, request)
        if res is False:
            return False

        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    last = float(res['data']['sell'])
                    return last

    def Orderbook(self):
        path = '/api/ticker/orderBook'
        request = {
            'pairName' : self.symbol,  # 币种对
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader' : sign,
        }
        res = self.http_request('POST', path, request, headers=headers)
        if not res:
            return False

        buy_list = []
        sell_list = []
        try:
            if isinstance(res, dict):
                if 'data' in res and res['data']:
                    if 'buyList' in res['data'] and res['data']['buyList']:
                        self.bids_price  = float(res['data']['buyList'][0]['price'])
                        self.bids_qty    = float(res['data']['buyList'][0]['amount'])
                    if 'sellList' in res['data'] and res['data']['sellList']:
                        self.asks_price  = float(res['data']['sellList'][0]['price'])
                        self.asks_qty    = float(res['data']['sellList'][0]['amount'])
                    return True
        except Exception as ex:
            print("Orderbook exception error %s" %ex)
        return False

    def Balance(self):
        path = '/api/account/balance'
        request = {
            'mbId'   : self.mbid,  #user id
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader' : sign,
        }
        res = self.http_request('POST', path, request, headers)
        if not res:
            return False
        self.targetBalance = self.baseBalance = 0
        if isinstance(res, dict):
            if 'data' in res and res['data']:
                if 'avail' in res['data'] and res['data']['avail']:
                    coins = res['data']['avail']
                    self.targetBalance = float(int(coins.get(self.target, 0)))
                    self.baseBalance   = float(int(coins.get(self.payment, 0)))
                    return True

        return False

    def Order(self, price, amount, side):
        path =  '/api/trade/orderPlace'
        request = {
            'mbId'   : self.mbid,  #user id
            'pairName' : self.symbol,
            'action' : 'ask' if side == 'SELL' else 'bid',
            'price'  : '%g' %price,
            'amount' : '%g' %amount,
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader' : sign,
        }
        content = self.http_request('POST', path, request, headers)
        if not content:
            return 'ERROR', 0, content

        order_id = 0
        status = 'ERROR'
        if 'status' in content:
            status = 'OK' if content['status'] == '0' else 'ERROR'
            if status == 'OK' and 'data' in content and content['data']:
                order_id = content['data'] #string
                if not order_id :
                    status = 'ERROR'
                    order_id = 0

        return status, order_id, content

    def Cancel(self, order_id, price, side):
        path = '/api/trade/orderCancel'
        request = {
            'mbId': self.mbid,  # user id
            'pairName': self.symbol,
            'ordNo': order_id,
            'action' : 'ask' if side == 'SELL' or 'ask' else 'bid',
            'ordPrice' : '%g' %price,
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader': sign,
        }
        res = self.http_request('POST', path, request, headers)
        return res

    def Order_info(self, side, cnt=20, skipIdx=0):
        '''
        주문체결 내역만 존재함.
        '''
        path =  '/api/account/signHistory'
        request = {
            'mbId': self.mbid,  # user id
            'pairName': self.symbol,
            'action' : 'ask' if side == 'SELL' or side == 'ask' else 'bid',
            'cnt' : str(cnt),         #Int	Number of result to fetch
            'skipIdx' : str(skipIdx)  #String	Number of skip count
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader': sign,
        }
        res = self.http_request('POST', path, request, headers)
        if not res:
            return False

        return res

    def _Order_info(self, side, cnt=20, skipIdx=0):
        '''
        모든 주문 내역이 존재함.   주문 체결 여부는 알 수 없음.
        '''
        path =  '/api/account/orderHistory'
        request = {
            'mbId': self.mbid,  # user id
            'pairName': self.symbol,
            'action' : 'ask' if side == 'SELL' or 'ask' else 'bid',
            'cnt' : str(cnt),         #Int	Number of result to fetch
            'skipIdx' : str(skipIdx)  #String	Number of skip count
        }
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader': sign,
        }
        res = self.http_request('POST', path, request, headers)
        if not res:
            return False

        return res

    def review_order(self, order_id, _qty, side):
        units_traded = 0
        resp = None
        find = False

        try:
            side = 'ask' if side == 'SELL' or side == 'ask' else 'bid'
            resp = self.Order_info(side)
            if 'status' in resp and resp['status'] == '0':
                if 'data' in resp and resp['data'] :
                    if 'list' in resp['data'] and resp['data']['list']:
                        orders = resp['data']['list']
                        if len(orders):
                            orders = sorted(orders, key=itemgetter('ordDt'), reverse=True)
                            for o in orders:
                                if str(o['ordNo']) == order_id:  # find it !
                                    find = True
                                    units_traded += float(o['signAmount'])
                                    avg_price = float(o['signPrice'])
                                    fee = float(o['fee'])

                            if find:
                                if units_traded == 0:   # unfilled
                                    return "GO", units_traded, avg_price, fee
                                elif units_traded < _qty : #partially filled
                                    print("units_traded %.4f" % units_traded)
                                    return "NG", units_traded, avg_price, fee
                                else:  # filled or canceled
                                    return "SKIP", units_traded, avg_price, fee

                            if not find:
                                logger.debug("it must be pending order")
                                return "GO", 0, 0, 0

            logger.debug("response error %s" % resp)
            return "SKIP", 0, 0, 0

        except Exception as ex:
            logger.debug("Exception error in review order {}-{}" .format(resp, ex))
            return "SKIP", 0, 0, 0