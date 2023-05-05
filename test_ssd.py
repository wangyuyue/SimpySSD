from sim import *
from ssd_estimate import logger, SSD, Cmd
from util import *

class None_App():
    def __init__(self):
        pass

    def process(self, cmd):
        pass

def get_rand_cmd(cmd_typ=None):
    if not cmd_typ:
        cmd_typ = 'read' if random.randint(0, 1) % 2 == 0 else 'write'
    return Cmd(rand_channel(), rand_chip(), cmd_typ = cmd_typ)

def check_chip_queue(ssd):
    for channel in ssd.channels:
        for chip in channel.chips:
            assert(len(chip.queued_cmd) == 0)

def check_channel_queue(ssd):
    for channel in ssd.channels:
        assert(len(channel.queued_cmd) == 0)

def check_ssd(ssd):
    assert(len(ssd.issued_cmd) == len(ssd.finished_cmd))

if __name__ == "__main__":
    for test in range(1):
        engine.now = 0
        Cmd.cmd_id = 0
        ssd = SSD(None_App())
        
        for i in range(random.randint(5, 40)):
            cmd = get_rand_cmd()
            ssd.issue(cmd)
        while len(engine.events) > 0:
            engine.exec()
        
        check_ssd(ssd)
        check_channel_queue(ssd)
        check_chip_queue(ssd)