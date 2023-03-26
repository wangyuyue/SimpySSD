from ssd_estimate import logger, engine, SSD, Cmd

class GNN:
    def __init__(self):
        self.gnn_time = 60
        self.sample = [5, 5, 2]
        self.n_hop = 3
        self.hop_map = {}
        self.batch = 32
        self.ssd = SSD(self)
        self.wait = True

    def get_cmd(self):
        return Cmd()

    def issue(self, cmd):
        self.hop_map[cmd] = 0
        self.issued = [cmd]
        self.to_issue = []

        self.ssd.issue(cmd)

    def process(self, cmd):
        # logger.debug(f"process {cmd}, pending: {self.issued}")
        self.issued.remove(cmd)
        cmd_hop = self.hop_map[cmd]
        if cmd_hop == self.n_hop:
            return
        to_sample = self.sample[cmd_hop]
        self.to_issue.extend([self.get_cmd() for i in range(to_sample)])
        if self.wait:
            if len(self.issued) == 0:
                for cmd in self.to_issue:
                    self.hop_map[cmd] = cmd_hop + 1
                    self.ssd.issue(cmd)
                self.issued = self.to_issue
                self.to_issue = []
            else:
                logger.debug(f"wait for other cmd in hop {cmd_hop}...")
        else:
            raise Exception("async not implemented")

gnn = GNN()
gnn.issue(gnn.get_cmd())

while len(engine.events) > 0:
    engine.exec()