# coding=utf-8
import time
import random
import math
from decimal import Decimal as D
from decimal import getcontext

import logging
logger = logging.getLogger(__name__)

# try:
#     from sitetrading.models import AutoBot, Trans
# except Exception as ex:
#     logger.debug('import error %s %s' %(__file__, ex))
#     raise ValueError

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

        if bot_conf.ex_max_qty:
            TradeSize = min(TradeSize, bot_conf.ex_max_qty)
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

        logger.debug(
            '{}@{}-{}/{} at {}{}'.format(qty, price, mode, bot_conf.mode, self.nickname, self.symbol))

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