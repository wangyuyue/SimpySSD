import random

params = {'channel bw': 800, # MB/s
         'read_latency': 40, # us
         'pg_sz': 8, # KB 
        'num_chip':16, 'num_channel':8}

class Engine:
    def __init__(self):
        self.events = []
        self.now = 0

    def add(self, event):
        self.events.append(event)
        self.events.sort(key=lambda x: x.time)

    def exec(self):
        event = self.events.pop(0)
        self.now = event.time
        obj = event.obj
        obj.exec(event)

engine = Engine()

class Event:
    def __init__(self, obj, func, time, args):
        self.obj = obj
        self.func = func
        self.time = time
        self.args = args


class Chip:
    def __init__(self, channel, idx):
        #print("Init a chip...")
        self.aval_time = 0
        self.read_latency = params['read_latency']
        self.channel = channel
        self.idx = idx
    def __repr__(self):
        return f"chip({self.channel.idx},{self.idx})"

    def enqueue(self, cmd):
        begin_time = max(engine.now, self.aval_time) 
        self.aval_time = begin_time + self.read_latency
        cmd.data_sz = params['pg_sz'] 
        engine.add(Event(self, 'read', begin_time, {'cmd':cmd}))
        #print(f'[{engine.now}]: {self} enqueue {cmd}')

    def read(self, cmd):
        print(f"[{engine.now}]: {self} read for {cmd}")
        engine.add(Event(self.channel, 'enqueue', engine.now + self.read_latency, {'cmd':cmd}))

    def exec(self, event):
        cmd = event.args['cmd']
        if event.func == 'read':
            self.read(cmd)
        elif event.func == 'enqueue':
            self.enqueue(cmd)

class Channel:
    def __init__(self, ssd, idx):
        #print("Init a channel...")
        self.aval_time = 0
        self.num_chip = params['num_chip']
        self.chips = [Chip(self, i) for i in range(self.num_chip)]
        self.bw = params['channel bw']
        self.ssd = ssd
        self.idx = idx

    def __repr__(self):
        return f"channel({self.idx})"

    def xfer_time(self, cmd):
        return cmd.data_sz / self.bw * 1000

    def enqueue(self, cmd):
        begin_time = max(engine.now, self.aval_time)
        self.aval_time = begin_time + self.xfer_time(cmd)
        engine.add(Event(self, 'xfer', begin_time, {'cmd':cmd}))
        #print(f"[{engine.now}]: {self} enqueue {cmd}")

    def xfer(self, cmd):
        engine.add(Event(self.ssd, 'get_result', engine.now + self.xfer_time(cmd), {'cmd':cmd}))
        print(f"[{engine.now}]: {self} transfer for {cmd}")
    

    def exec(self, event):
        cmd = event.args['cmd']
        if event.func == 'xfer':
            self.xfer(cmd)
        elif event.func == 'enqueue':
            self.enqueue(cmd)

class SSD:
    def __init__(self, app):
        self.aval_time = 0
        self.num_channel = params['num_channel']
        self.channels = [Channel(self, i) for i in range(self.num_channel)]
        self.app = app

    def get_result(self, cmd):
        print(f'[{engine.now}]: ssd get page for {cmd}')
        self.app.process(cmd)

    def issue(self, cmd):
        print(f'ssd issue cmd {cmd.id}')
        channel = self.channels[cmd.channel_id]
        chip = channel.chips[cmd.chip_id]
        engine.add(Event(chip, 'enqueue', engine.now, {'cmd':cmd}))

    def exec(self, event):
        if event.func == 'get_result':
            self.get_result(event.args['cmd'])
        else:
            raise Exception("hello world")

class Cmd:
    cmd_id = 0
    def __init__(self, channel_id = None, chip_id = None):
        if channel_id:
            self.channel_id = channel_id
        else:
            self.channel_id = random.randint(0, params['num_channel'] - 1)

        if chip_id:
            self.chip_id = chip_id
        else:
            self.chip_id = random.randint(0, params['num_chip'] - 1)
        Cmd.cmd_id += 1
        self.id = Cmd.cmd_id
    def __repr__(self):
        return f"cmd({self.id})"


class GNN:
    def __init__(self):
        self.gnn_time = 60
        self.sample = [5, 5]
        self.n_hop = 2
        self.hop_map = {}
        self.batch = 32
        self.ssd = SSD(self)
        self.wait = True

    def issue(self):
        cmd = Cmd()
        self.hop_map[cmd] = 0
        self.issued = [cmd]
        self.to_issue = []

        self.ssd.issue(cmd)

    def process(self, cmd):
        self.issued.remove(cmd)
        cmd_hop = self.hop_map[cmd]
        if cmd_hop == self.n_hop:
            return
        to_sample = self.sample[cmd_hop]
        self.to_issue.extend([Cmd() for i in range(to_sample)])
        if self.wait:
            if len(self.issued) == 0:
                for cmd in self.to_issue:
                    self.hop_map[cmd] = cmd_hop + 1
                    self.ssd.issue(cmd)
                self.issued = self.to_issue
                self.to_issue = []
            else:
                print(f"wait for other cmd in hop {cmd_hop}...")
        else:
            print("async not implemented")

gnn = GNN()
gnn.issue()

while len(engine.events) > 0:
    engine.exec()
