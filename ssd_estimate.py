import random
import logging
from sim import *
from util import *


logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('ssd_logger')
logger.setLevel(logging.INFO)

def assert_equal(x, y):
    try:
        assert(x == y)
    except AssertionError:
        logger.error(x, y)
        raise

class SRAM_Buffer:
    idle = 0
    transferring = 1
    ready_to_transfer = 2
    executing = 3
    ready_to_execute = 4
    def __init__(self):
        self.cmd = None
        self.size = ssd_params['pg_sz']
        self.empty = True

class Chip(Sim):
    def __init__(self, channel, idx):
        logger.info("Init a chip...")
        self.channel = channel
        self.ssd = channel.ssd
        self.idx = idx

        self.avail_time = 0

        self.read_latency = ssd_params['read_latency']
        self.write_latency = ssd_params['write_latency']

        self.queued_cmd = []

        self.buffer = [SRAM_Buffer(), SRAM_Buffer()]
        # cmd <- None when the operation can step to the next stage (not stalled)
        self.exec_cmd = None
        self.transfer_cmd = None

        # done <- True when the operation finish
        self.exec_done = True
        self.transfer_done = True

    def cmd_in_buf(self, cmd):
        for buf in self.buffer:
            if not buf.empty and buf.cmd == cmd:
                return buf
        return None

    def exec(self, cmd, buf):
        self.exec_cmd = cmd
        self.exec_done = False
        if cmd.cmd_typ == 'read':
            self.queued_cmd.remove(cmd)
            buf.empty = False
            buf.cmd = cmd
            buf.status = SRAM_Buffer.executing
        elif cmd.cmd_typ == 'write':
            buf.status = SRAM_Buffer.executing

    def __repr__(self):
        return f"chip({self.channel.idx},{self.idx})"

    def next_idle(self):
        return max(engine.now, self.avail_time)

    def check_exec(self):
        if not (self.exec_cmd is None and self.exec_done):
            return
        for buf in self.buffer:
            if buf.empty:
                continue
            cmd = buf.cmd
            if cmd.cmd_typ == 'write' and buf.status == SRAM_Buffer.ready_to_execute:
                self.write_begin(cmd, buf)
                return

        for buf in self.buffer:
            if not buf.empty:
                continue
            if len(self.queued_cmd) > 0:
                cmd = self.queued_cmd[0]
                if cmd.cmd_typ == 'read':
                    self.read_begin(cmd, buf)
                    return

    def check_transfer(self):
        def prepare_transfer(cmd):
            if not cmd in self.channel.queued_cmd:
                logger.debug(f"add {cmd} to {self.channel} queue")
                self.channel.queued_cmd.append(cmd)
            self.channel.check_transfer()
        
        for buf in self.buffer:
            if not buf.empty:
                cmd = buf.cmd
                if cmd.cmd_typ == 'read' and buf.status == SRAM_Buffer.ready_to_transfer:
                    prepare_transfer(cmd)

        if len(self.queued_cmd) > 0:
            cmd = self.queued_cmd[0]
            if cmd.cmd_typ == 'write' and self.transfer_cmd is None:
                self.queued_cmd.pop(0)
                prepare_transfer(cmd)

    def read_begin(self, cmd, buf):
        assert_equal(cmd, self.queued_cmd[0])
        self.exec(cmd, buf)
        self.next_avail_time = engine.now + self.read_latency
        logger.debug(f"[{engine.now}]: {self} read_begin {cmd}")
        engine.add(Event(self, 'read_finish', engine.now + self.read_latency, {'buf':buf}))

    def read_finish(self, buf):
        cmd = buf.cmd
        logger.debug(f"[{engine.now}]: {self} read_finish {cmd}")
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_cmd = None
        self.exec_done = True
        buf.status = SRAM_Buffer.ready_to_transfer
        self.check_transfer()

        self.check_exec() # unnecessary because if check_transfer begins an transfer, transfer_begin will do chip.check_exec()

    def write_begin(self, cmd, buf):
        logger.debug(f"[{engine.now}]: {self} write for {cmd}")

        self.exec(cmd, buf)
        self.check_transfer()
        self.next_avail_time = engine.now + self.write_latency
        engine.add(Event(self, 'write_finish', engine.now + self.write_latency, {'buf': buf}))

    def write_finish(self, buf):
        cmd = buf.cmd
        logger.debug(f"[{engine.now}]: {self} write_finish {cmd}")
        
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_cmd = None
        self.exec_done = True
        
        buf.status = SRAM_Buffer.idle
        buf.empty = True
        buf.cmd = None

        assert(not cmd in self.ssd.finished_cmd)
        self.ssd.finished_cmd.add(cmd)

        self.check_exec()
        self.channel.check_transfer()

    def do(self, event):
        buf = event.args['buf']
        if event.func == 'read_finish':
            self.read_finish(buf)
        elif event.func == 'write_finish':
            self.write_finish(buf)
        else:
            super().do(event)

class Channel(Sim):
    def __init__(self, ssd, idx):
        logger.info("Init a channel...")
        self.ssd = ssd
        self.idx = idx
        self.aval_time = 0

        self.bw = ssd_params['channel bw']

        self.num_chip = ssd_params['num_chip']
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

        def find_transferrable():
            for cmd in self.queued_cmd:
                if cmd.cmd_typ == 'read':
                    return cmd
                elif cmd.cmd_typ == 'write':
                    chip = self.chips[cmd.chip_id]
                    empty_buf = [buf for buf in chip.buffer if buf.empty]
                    if len(empty_buf) > 0:
                        return cmd
            return None

        # begin transfer
        cmd = find_transferrable()
        if cmd is None:
            return
        
        self.queued_cmd.remove(cmd)
        self.transfer_begin(cmd)

    def transfer_begin(self, cmd):
        logger.debug(f"[{engine.now}]: {self} transfer_begin {cmd}")
        chip = self.chips[cmd.chip_id]
        assert_equal(chip.transfer_cmd, None)
        assert_equal(self.transfer_cmd, None)

        self.transfer_cmd = cmd
        if cmd.cmd_typ == 'read':
            buf = chip.cmd_in_buf(cmd)
            assert(buf != None)
            buf.status = SRAM_Buffer.transferring
            engine.add(Event(self, 'transfer_finish', engine.now + self.transfer_time(cmd), {'cmd': cmd}))
            chip.check_exec() # necessary for read write interleaved situation
        elif cmd.cmd_typ == 'write':
            empty_bufs = [buf for buf in chip.buffer if buf.empty]
            buf = empty_bufs[0]
            buf.cmd = cmd
            buf.empty = False
            buf.status = SRAM_Buffer.transferring
            engine.add(Event(self, 'transfer_finish', engine.now + self.transfer_time(cmd), {'cmd': cmd}))        

        chip.transfer_cmd = cmd
        chip.transfer_done = False

    def transfer_finish(self, cmd):
        logger.debug(f"[{engine.now}]: {self} transfer_finish {cmd}")
        chip = self.chips[cmd.chip_id]
        assert_equal(cmd, self.transfer_cmd)
        assert_equal(cmd, chip.transfer_cmd)

        self.transfer_cmd = None
        
        chip.transfer_cmd = None
        chip.transfer_done = True

        buf = chip.cmd_in_buf(cmd)
        if cmd.cmd_typ == 'read':
            buf.status = SRAM_Buffer.idle
            buf.empty = True
            buf.cmd = None
            assert(not cmd in self.ssd.finished_cmd)
            self.ssd.finished_cmd.add(cmd)
            engine.add(Event(self.ssd, 'get_result', engine.now, {'cmd': cmd}))
        elif cmd.cmd_typ == 'write':
            buf.status = SRAM_Buffer.ready_to_execute
        chip.check_exec()
        self.check_transfer()
        chip.check_transfer()
    
    def do(self, event):
        cmd = event.args['cmd']
        if event.func == 'transfer_finish':
            self.transfer_finish(cmd)
        else:
            super().do(event)


class SSD(Sim):
    def __init__(self, system):
        logger.info("Init SSD...")
        self.aval_time = 0
        self.num_channel = ssd_params['num_channel']
        self.num_chip = ssd_params['num_chip']
        self.channels = [Channel(self, i) for i in range(self.num_channel)]
        
        self.system = system

        self.issued_cmd = set()
        self.finished_cmd = set()

    def queue(self, channel_id, chip_id):
        return self.channels[channel_id].chips[chip_id].queued_cmd

    def get_result(self, cmd):
        logger.info(f'[{engine.now}]: ssd get_result {cmd}')
        self.system.process(cmd)

    def issue(self, cmd):
        logger.info(f'[{engine.now}]: ssd issue {cmd}')
        self.issued_cmd.add(cmd)

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
        self.channel_id = channel_id or rand_channel()
        self.chip_id = chip_id or rand_chip()
        self.cmd_typ = cmd_typ
        self.data_sz = ssd_params['pg_sz']

        Cmd.cmd_id += 1
        self.id = Cmd.cmd_id
    def __repr__(self):
        typ = 'r' if self.cmd_typ == 'read' else 'w'
        return f"cmd{typ}({self.id}[{self.channel_id},{self.chip_id}])"


