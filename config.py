
class Params(object):

    def __init__(self):
        self.fr_qty = 0
        self.to_qty = 0
        self.fr_price = 0
        self.to_price = 0
        self.fr_time = 0
        self.to_time = 0
        self.fr_off = 0
        self.to_off = 0
        self.mode = None
        self.dryrun = True
        self.ex_min_qty = 0
        self.ex_max_qty = 10000
        self.mid_price = 0
        self.tick_interval = 0

    '''
    # https://dojang.io/mod/page/view.php?id=2476
    @property
    def fr_qty(self):
        return self.fr_qty

    @fr_qty.setter
    def fr_qty(self, value):
        self.fr_qty = value
    '''


ps = Params()