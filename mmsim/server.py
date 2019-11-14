import struct
from pathlib import Path
from threading import Thread

import zmq

from mmsim.mazes import read_walls


class Server(Thread):
    def __init__(self, host='127.0.0.1', port='6574'):
        super().__init__()
        self.context = zmq.Context()
        self.reply = self.context.socket(zmq.REP)
        self.reply.bind('tcp://{host}:{port}'.format(host=host, port=port))

        self.poller = zmq.Poller()
        self.poller.register(self.reply, zmq.POLLIN)

        self.running = True

        self.reset()

    def reset(self):
        self.maze = None
        self.history = []

    def set_maze(self, path: Path):
        self.reset()
        template = load_maze(path)
        self.maze.reset(template)

    def run(self):
        while self.running:
            events = dict(self.poller.poll(10))
            if not events:
                continue
            self.process_events(events)

    def process_events(self, events):
        for socket in events:
            if events[socket] != zmq.POLLIN:
                continue
            self.process_request(socket.recv())

    def process_request(self, message):
        if message.startswith(b'W'):
            position = message.lstrip(b'W')
            x, y, direction = struct.unpack('3B', position)
            walls = read_walls(self.maze, x, y, chr(direction))
            self.reply.send(struct.pack('3B', *walls))
            return
        if message.startswith(b'S'):
            state = message.lstrip(b'S')
            self.history.append(state)
            self.reply.send(b'ok')
            return
        if message == b'reset':
            self.reset()
            self.reply.send(b'ok')
            return
        if message == b'ping':
            self.reply.send(b'pong')
            return
        raise ValueError('Unknown message received! "{}"'.format(message))


if __name__ == '__main__':
    server = Server().loop()
