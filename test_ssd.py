from ssd_estimate import logger, engine, SSD, GNNAcc, Cmd
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

if __name__ == "__main__":
    for test in range(1):
        engine.now = 0
        ssd = SSD(None_App())
        
        # for i in range(10):
        #     cmd = get_rand_cmd()
        #     ssd.issue(cmd)
        cmd = get_rand_cmd('read')
        ssd.issue(cmd)
        cmd = get_rand_cmd('write')
        ssd.issue(cmd)
        while len(engine.events) > 0:
            engine.exec()
        chips = ssd.channels[0].chips
        for chip in chips:
            assert(len(chip.queued_cmd) == 0)
        assert(len(ssd.channels[0].queued_cmd) == 0)