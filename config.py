
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
        self.dryrun = False
        self.ex_min_qty = 0
        self.ex_max_qty = 0
        self.mid_price = 0
        self.tick_interval = 0
        self.run_flag = 0

ps = Params()