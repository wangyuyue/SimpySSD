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