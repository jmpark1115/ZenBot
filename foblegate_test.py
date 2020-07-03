from foblgate import Foblgate

if __name__ == '__main__':
    symbol = 'ZEN/KRW'
    connect_key ='9b901f49bab0bffb'
    secret_key = '56febbab81ee53a5'
    foblgate = Foblgate('0', connect_key, secret_key, 'xen', 'krw')
    foblgate.Orderbook()
    print("ORDERBOOK \nASKS : {:10.0f} @ {:.8f} \nBIDS : {:10.0f} @ {:.8f}" \
                .format(foblgate.asks_qty, foblgate.asks_price,
                        foblgate.bids_qty, foblgate.bids_price))
    print('Balance')
    foblgate.Balance()
    print("BALANCE\n**(tBal: {:.8f}) | (bBal: {:.8f})**"
                .format(foblgate.targetBalance, foblgate.baseBalance))
    print('end of all')

    # sell
    price  =  foblgate.bids_price
    side   =  'SELL'
    qty =  1000

    # buy
    # price  =  foblgate.asks_price
    # side   =  'BUY'
    # qty =  750

    # status, order_id, content = foblgate.Order(price, qty, side)
    # print(status, order_id, content)

    '''
    # order_id = '200703251880'  # 기 cancel 된 order_id 를 cancel 다시 시도
    resp = foblgate.Cancel(order_id, side, price)
    print(resp)
    '''

    order_id = '200703334082'
    resp = foblgate.review_order(order_id, qty, side)
    print(resp)
