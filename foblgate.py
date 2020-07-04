import time
import hashlib
from operator import itemgetter
import hmac
import requests

import logging
logger = logging.getLogger(__name__)

try:
    from ZenBot.views_common import Common
except Exception as ex:
    raise ValueError

# https://api-document.foblgate.com/
API_URL = 'https://api2.foblgate.com'
# API_URL = 'https://qao-qao-api2.foblgate.com'

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