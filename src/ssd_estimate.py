import random
import logging
from sim import *
from util import *
from ssd_config import ssd_config

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger('ssd_logger')
# logger.setLevel(logging.DEBUG)
logger.setLevel(0)
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
        self.size = ssd_config.pg_sz_kb
        self.empty = True

class Chip(Sim):
    def __init__(self, channel, idx):
        # logger.info("Init a chip...")
        self.channel = channel
        self.ssd = channel.ssd
        self.idx = idx

        self.avail_time = 0

        self.read_latency = ssd_config.read_latency_us
        self.write_latency = ssd_config.write_latency_us

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

    def record_flash_stat(self):
        stat = self.channel.ssd.system.stat
        if stat is None:
            return
        
        delta = 1 if self.exec_cmd else -1
        stat.chip_busy(engine.now, delta)
        if self.exec_cmd is None:
            return
        hop_i = self.channel.ssd.system.app.cmd2hop[self.exec_cmd]
        stat.start_hop(engine.now, hop_i)

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
        elif cmd.cmd_typ == 'sample':
            self.queued_cmd.remove(cmd)
            buf.empty = False
            buf.cmd = cmd
            buf.status = SRAM_Buffer.executing
        else:
            raise Exception("Unknown command type")
        self.record_flash_stat()
        stat = self.ssd.system.stat
        if stat is not None:
            stat.cmd_stat[cmd].set_time('read_begin', engine.now)

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
                elif cmd.cmd_typ == 'sample':
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
                elif cmd.cmd_typ == 'sample' and buf.status == SRAM_Buffer.ready_to_transfer:
                    prepare_transfer(cmd)

        if len(self.queued_cmd) > 0:
            cmd = self.queued_cmd[0]
            if cmd.cmd_typ == 'write' and self.transfer_cmd is None:
                self.queued_cmd.pop(0)
                prepare_transfer(cmd)

    def read_begin(self, cmd, buf):
        assert_equal(cmd, self.queued_cmd[0])
        self.exec(cmd, buf)
        logger.debug(f"[{engine.now}]: {self} read_begin {cmd}")
        engine.add(Event(self, 'read_finish', engine.now + self.read_latency, {'buf':buf}))

    def read_finish(self, buf):
        cmd = buf.cmd
        logger.debug(f"[{engine.now}]: {self} read_finish {cmd}")
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_cmd = None
        self.exec_done = True

        self.record_flash_stat()

        if cmd.cmd_typ == 'read':
            buf.status = SRAM_Buffer.ready_to_transfer
            self.check_transfer()
        elif cmd.cmd_typ == 'sample':
            self.sample_begin(buf)
        self.check_exec() # unnecessary because if check_transfer begins an transfer, transfer_begin will do chip.check_exec()

    def sample_begin(self, buf):
        buf.status = SRAM_Buffer.idle
        sample_latency = 0.2
        cmd = buf.cmd
        if cmd.has_feat:
            sample_latency += graph_params['feat_sz'] / 1365
        engine.add(Event(self, 'sample_finish', engine.now + sample_latency, {'buf':buf}))

    def sample_finish(self, buf):
        buf.status = SRAM_Buffer.ready_to_transfer
        cmd = buf.cmd
        
        cmd.data_sz = 0
        if cmd.has_feat:
            cmd.data_sz = graph_params['feat_sz']
        if cmd.has_ext:
            ext_cmds = self.ssd.system.app.cmd2extcmds[cmd]
            self.ssd.forward(ext_cmds)
        self.check_transfer()

    def write_begin(self, cmd, buf):
        logger.debug(f"[{engine.now}]: {self} write for {cmd}")

        self.exec(cmd, buf)
        self.check_transfer()
        engine.add(Event(self, 'write_finish', engine.now + self.write_latency, {'buf': buf}))

    def write_finish(self, buf):
        cmd = buf.cmd
        logger.debug(f"[{engine.now}]: {self} write_finish {cmd}")
        
        assert_equal(self.exec_cmd, cmd)
        assert(not self.exec_done)
        self.exec_cmd = None
        self.exec_done = True

        self.record_flash_stat()
        
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
        elif event.func == 'sample_finish':
            self.sample_finish(buf)
        else:
            super().do(event)

class Channel(Sim):
    def __init__(self, ssd, idx):
        # logger.info("Init a channel...")
        self.ssd = ssd
        self.idx = idx
        self.avail_time = 0

        self.bw = ssd_config.channel_bw_mbps

        self.num_chip = ssd_config.num_chip
        self.chips = [Chip(self, i) for i in range(self.num_chip)]

        self.transfer_cmd = None
        self.queued_cmd = []

        # self.next_issue_time = 0
        # self.issue_queue = []
        # self.forward_queue = []

    def __repr__(self):
        return f"channel({self.idx})"

    def record_channel_stat(self, is_busy):
        stat = self.ssd.system.stat
        if stat is None:
            return
        
        delta = 1 if is_busy else -1
        stat.channel_busy(engine.now, delta)

    def next_idle(self):
        return max(engine.now, self.avail_time)

    def transfer_time(self, cmd):
        return cmd.data_sz / self.bw

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
                elif cmd.cmd_typ == 'sample':
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
        elif cmd.cmd_typ == 'sample':
            buf = chip.cmd_in_buf(cmd)
            assert(buf != None)
            buf.status = SRAM_Buffer.transferring
            engine.add(Event(self, 'transfer_finish', engine.now + self.transfer_time(cmd), {'cmd': cmd}))
            chip.check_exec() # necessary for read write interleaved situation

        chip.transfer_cmd = cmd
        chip.transfer_done = False
        
        self.record_channel_stat(is_busy=True)
        stat = self.ssd.system.stat
        if stat is not None:
            stat.cmd_stat[cmd].set_time('transfer_begin', engine.now)

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
        elif cmd.cmd_typ == 'sample':
            buf.status = SRAM_Buffer.idle
            buf.empty = True
            buf.cmd = None
            assert(not cmd in self.ssd.finished_cmd)
            self.ssd.finished_cmd.add(cmd)
            engine.add(Event(self.ssd, 'get_result', engine.now, {'cmd': cmd}))
        
        self.record_channel_stat(is_busy=False)
        stat = self.ssd.system.stat
        if stat is not None:
            stat.cmd_stat[cmd].set_time('transfer_end', engine.now)

        chip.check_exec()
        self.check_transfer()
        chip.check_transfer()
    
    # def push_to_forward_queue(self, cmd):
    #     self.forward_queue.append(cmd)
    #     self.ssd.forward_cmd()

    def do(self, event):
        cmd = event.args['cmd']
        if event.func == 'transfer_finish':
            self.transfer_finish(cmd)
        # elif event.func == 'push_to_forward_queue':
        #     self.push_to_forward_queue(cmd)
        else:
            super().do(event)


class SSD(Sim):
    def __init__(self, system):
        # logger.info("Init SSD...")
        self.aval_time = 0
        self.num_channel = ssd_config.num_channel
        self.num_chip = ssd_config.num_chip
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

    def forward(self, ext_cmds):
        for ext_cmd in ext_cmds:
            self.system.app.issue(ext_cmd)

    def do(self, event):
        if event.func == 'get_result':
            self.get_result(event.args['cmd'])
        else:
            super().do(event)

class Cmd:
    cmd_id = 0
    def __init__(self, cmd_typ, channel_id, chip_id, page_id = None, data_sz = None):
        self.cmd_typ = cmd_typ

        self.page_id = page_id
        self.channel_id = channel_id
        self.chip_id = chip_id
        
        self.data_sz = data_sz or ssd_config.pg_sz_kb * 1e3
        self.has_ext = False
        self.has_feat = False

        Cmd.cmd_id += 1
        self.id = Cmd.cmd_id
    def __repr__(self):
        cmd_typs = {'read':'r', 'write':'w', 'sample':'s'}
        typ = cmd_typs[self.cmd_typ]
        
        return f"cmd{typ}({self.id}[{self.channel_id},{self.chip_id}])"


