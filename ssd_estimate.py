import random
import logging
logging.basicConfig()
logger = logging.getLogger(':')
logger.setLevel(logging.INFO)

params = {'channel bw': 800, # MB/s
         'read_latency': 40, # us
         'write_latency': 100, # us
         'pg_sz': 8, # KB 
        'num_chip':16, 'num_channel':8}

def assert_equal(x, y):
    try:
        assert(x == y)
    except AssertionError:
        logger.error(x, y)
        raise

class Engine:
    engine = None
    def __init__(self):
        assert(Engine.engine is None)
        Engine.engine = self
        self.events = []
        self.now = 0

    def add(self, event):
        self.events.append(event)
        self.events.sort(key=lambda x: x.time)

    def exec(self):
        event = self.events.pop(0)
        self.now = event.time
        obj = event.obj
        obj.do(event)

engine = Engine()

class Event:
    def __init__(self, obj, func, time, args):
        self.obj = obj
        self.func = func
        self.time = time
        self.args = args

class Sim:
    def do(self, event):
        raise Exception(f"{self}: unsupport event [{event.func}]")

class Chip(Sim):
    def __init__(self, channel, idx):
        logger.info("Init a chip...")
        self.channel = channel
        self.ssd = channel.ssd
        self.idx = idx

        self.avail_time = 0

        self.read_latency = params['read_latency']
        self.write_latency = params['write_latency']

        self.queued_cmd = []

        # cmd <- None when the operation can step to the next stage (not stalled)
        self.exec_cmd = None
        self.transfer_cmd = None

        # done <- True when the operation finish
        self.exec_done = True
        self.transfer_done = True

    def exec(self, cmd):
        self.exec_cmd = cmd
        self.exec_done = False
        self.queued_cmd.remove(cmd)

    def transfer(self, cmd):
        self.transfer_cmd = cmd
        self.transfer_done = False
        self.queued_cmd.remove(cmd)

    def exec_complete_pending(self):
        return self.exec_done and not self.exec_cmd is None

    def transfer_complete_pending(self):
        return self.transfer_done and not self.transfer_cmd is None

    def __repr__(self):
        return f"chip({self.channel.idx},{self.idx})"

    def next_idle(self):
        return max(engine.now, self.avail_time)

    def check_exec(self):
        if not (self.exec_cmd is None and self.exec_done):
            return
        cmd = self.transfer_cmd
        if cmd and cmd.cmd_typ == 'write' and self.transfer_done:
            self.write_begin(cmd)
            return
        if len(self.queued_cmd) > 0:
            cmd = self.queued_cmd[0]
            if cmd.cmd_typ == 'read':
                self.read_begin(cmd)

    def check_transfer(self):
        if not (self.transfer_cmd is None and self.transfer_done):
            return
        cmd = self.exec_cmd
        if cmd and cmd.cmd_typ == 'read' and self.exec_done:
            logger.debug(f"add {cmd} to {self.channel} queue")
            self.channel.queued_cmd.append(cmd)
            self.channel.check_transfer()
            return
        if len(self.queued_cmd) > 0:
            if self.queued_cmd[0].cmd_typ == 'write':
                self.channel.queued_cmd.append(self.queued_cmd[0])
                self.channel.check_transfer()

    def read_begin(self, cmd):
        assert_equal(cmd, self.queued_cmd[0])
        self.exec(cmd)
        self.next_avail_time = engine.now + self.read_latency
        logger.debug(f"[{engine.now}]: {self} read_begin {cmd}")
        engine.add(Event(self, 'read_finish', engine.now + self.read_latency, {'cmd':cmd}))

    def read_finish(self, cmd):
        logger.debug(f"[{engine.now}]: {self} read_finish {cmd}")
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_done = True
        self.check_transfer()

        self.check_exec() # unnecessary because if check_transfer begins an transfer, transfer_begin will do chip.check_exec()

    def write_begin(self, cmd):
        logger.debug(f"[{engine.now}]: {self} chip write for {cmd}")
        assert_equal(self.transfer_cmd, cmd)
        assert(self.transfer_done)
            
        self.transfer_cmd = None
        self.exec(cmd)
        self.check_transfer()
        self.next_avail_time = engine.now + self.write_latency
        engine.add(Event(self, 'write_finish', engine.now + self.write_latency, {'cmd': cmd}))

    def write_finish(self, cmd):
        logger.debug(f"[{engine.now}]: {self} write_finish {cmd}")
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_cmd = None
        self.exec_done = True
        self.check_exec()

    def do(self, event):
        cmd = event.args['cmd']
        if event.func == 'read_finish':
            self.read_finish(cmd)
        elif event.func == 'write_finish':
            self.write_finish(cmd)
        else:
            super().do(event)

class Channel(Sim):
    def __init__(self, ssd, idx):
        logger.info("Init a channel...")
        self.ssd = ssd
        self.idx = idx
        self.aval_time = 0

        self.bw = params['channel bw']

        self.num_chip = params['num_chip']
        self.chips = [Chip(self, i) for i in range(self.num_chip)]

        self.transfer_cmd = None
        self.queued_cmd = []

    def __repr__(self):
        return f"channel({self.idx})"

    def next_idle(self):
        return max(engine.now, self.avail_time)

    def transfer_time(self, cmd):
        return cmd.data_sz / self.bw * 1000

    def check_transfer(self):
        if self.transfer_cmd or len(self.queued_cmd) == 0:
            return

        # begin transfer
        cmd = self.queued_cmd.pop(0)
        self.transfer_begin(cmd)

    def transfer_begin(self, cmd):
        logger.debug(f"[{engine.now}]: {self} transfer_begin {cmd}")
        chip = self.chips[cmd.chip_id]
        assert_equal(chip.transfer_cmd, None)
        assert_equal(self.transfer_cmd, None)

        self.transfer_cmd = chip.transfer_cmd = cmd
        chip.transfer_done = False

        if cmd.cmd_typ == 'read':
            assert(chip.exec_cmd == cmd)
            chip.exec_cmd = None
            engine.add(Event(self, 'transfer_finish', engine.now + self.transfer_time(cmd), {'cmd': cmd}))
            chip.check_exec()
        elif cmd.cmd_typ == 'write':
            engine.add(Event(self, 'transfer_finish', engine.now + self.transfer_time(cmd), {'cmd': cmd}))        

    def transfer_finish(self, cmd):
        logger.debug(f"[{engine.now}]: {self} transfer_finish {cmd}")
        chip = self.chips[cmd.chip_id]
        assert_equal(cmd, self.transfer_cmd)
        assert_equal(cmd, chip.transfer_cmd)

        self.transfer_cmd = None
        chip.transfer_done = True
        
        if cmd.cmd_typ == 'read':
            chip.transfer_cmd = None
            engine.add(Event(self.ssd, 'get_result', engine.now, {'cmd': cmd}))
        elif cmd.cmd_typ == 'write':
            chip.check_exec()
        self.check_transfer()
    
    def do(self, event):
        cmd = event.args['cmd']
        if event.func == 'transfer_finish':
            self.transfer_finish(cmd)
        else:
            super().do(event)


class SSD(Sim):
    def __init__(self, app):
        logger.info("Init SSD...")
        self.aval_time = 0
        self.num_channel = params['num_channel']
        self.num_chip = params['num_chip']
        self.channels = [Channel(self, i) for i in range(self.num_channel)]
        self.app = app

    def queue(self, channel_id, chip_id):
        return self.channels[channel_id].chips[chip_id].cmd_queue

    def get_result(self, cmd):
        logger.info(f'[{engine.now}]: ssd get_result {cmd}')
        self.app.process(cmd)

    def issue(self, cmd):
        logger.info(f'[{engine.now}]: ssd issue {cmd}')
        channel = self.channels[cmd.channel_id]
        chip = channel.chips[cmd.chip_id]
        chip.queued_cmd.append(cmd)
        chip.check_exec()
        chip.check_transfer()

    def do(self, event):
        if event.func == 'get_result':
            self.get_result(event.args['cmd'])
        else:
            super().do(event)

class Cmd:
    cmd_id = 0
    def __init__(self, channel_id = None, chip_id = None, cmd_typ = 'read'):
        self.channel_id = channel_id or random.randint(0, params['num_channel'] - 1)
        self.chip_id = chip_id or random.randint(0, params['num_chip'] - 1)
        self.cmd_typ = cmd_typ
        self.data_sz = params['pg_sz']

        Cmd.cmd_id += 1
        self.id = Cmd.cmd_id
    def __repr__(self):
        return f"cmd({self.id}[{self.channel_id},{self.chip_id}])"


