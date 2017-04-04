"""
Websockets, but a bit neater. It's greatly based on Socket.io, but only supports websockets. It will have events.
No namespaces or rooms. Those would be handled by the websocket url.

It takes in data in the form of:

[event][json]

However, json must be an array or object.

Examples:
    memes{"foo": "bar"}
    #!@c["test", {"is": ["a", 4], "success"}]
Non-examples:
    {"yer": 4}
    [dsa
    asdf"hohoho"
"""
import json
import logging
import re

from tornado import websocket

_logger = logging.getLogger('eventsocket')


class EventSocketRouter:
    """
    Controls all the eventsockets.
    """

    def __init__(self):
        self.listeners = {}
        self.sockets = []
        self._next_sid = 0
        self.on_open = lambda s: _logger.warning('Socket open event undefined, not triggering it')
        self.on_close = lambda s: _logger.warning('Socket close event undefined, not triggering it')

    def __repr__(self):
        return 'EventSocketRouter(hash={})'.format(hash(self))

    def get_socket_by_id(self, id):
        try:
            return self.sockets[id]
        except IndexError:
            return None

    def register_listener(self, event: str, listener: callable):
        self.listeners[event] = listener

    def register_socket(self, socket):
        self.sockets.append(socket)
        self._next_sid += 1
        return self._next_sid - 1

    def on(self, arg):
        """
        A shorthand for register_listener. It can be used as a function or a decorator. If arg is a string, 
        it registers that as the listener. Without any args, it is a decorator that takes the name of the function 
        and uses that as the event name. Example of usage: 
        
        :Example:
        
        code-block::
            @router.on
            def event():
                ...
            # is equivalent to
            @router.on('event')
            def listener():
                ....
        
        :param arg: a string or function
        
        :return: a decorator function or a regular function depending on input
        """
        if type(arg) == str:  # Take-in-argument mode
            def decorator(func):
                self.register_listener(arg, func)
                return func
            return decorator

        elif callable(arg):  # Decorator mode
            self.register_listener(arg.__name__, arg)
            return arg

        else:
            raise TypeError

    def on_received_message(self, event, data, socket):
        try:
            self.listeners[event](data, socket)
        except KeyError or IndexError:
            _logger.warning('No listener was found for event "%s"', event)


class EventSocketHandler(websocket.WebSocketHandler):

    def __repr__(self):
        return 'EventSocketHandler(router={}, hash={})'.format(self.router, hash(self))

    # noinspection PyMethodOverriding
    def initialize(self, router):
        self.router = router
        self.id = None
        self.url_param = None
        self.count = 0

    def open(self, url_param=''):
        print(self.router)
        _logger.info('new connection established with url_param: %s', url_param)
        self.add_to_router()
        self.url_param = url_param

    def add_to_router(self):
        self.id = self.router.register_socket(self)
        _logger.info('registered socket #%s', self.id)
        self.router.on_open(self)

    def on_message(self, message):
        _logger.debug('socket #%s recieved message #%s: %s', self.id, self.count, message)
        try:
            match = re.match(r'(.+)((?:[{\[]).+)', message)  # Ensure that it matches the described format
            event = match.group(1)
            encoded_data = match.group(2)
            data = json.loads(encoded_data)  # Ensure that it's a valid JSON
            self.router.on_received_message(event, data, self)
            _logger.info('socket #%s triggered event "%s" by message #%s', self.id, self.count, event)
        except json.decoder.JSONDecodeError:
            # Do nothing because it's not valid JSON
            _logger.warning('socket #%s dropped message #%s due to improper format: %s', self.id, self.count,
                            message)

        self.count += 1

    def on_close(self):
        self.router.sockets.remove(self)
        self.router.on_close(self)
        _logger.info('Disconnected')

    def emit(self, event: str, data):
        to_send = '{event}{json}'.format(event=event, json=json.dumps(data))
        self.write_message(to_send)


if __name__ == '__main__':
    pass
