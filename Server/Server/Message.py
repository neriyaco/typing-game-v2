from json import dumps, loads, JSONEncoder, JSONDecoder

CMD = "code"
MSG = "data"


class MessageEncoder(JSONEncoder):
    def default(self, o):
        return {CMD: o.command, MSG: o.data}


class MessageDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self._from_json, *args, **kwargs)

    def _from_json(self, obj):
        return Message(obj[CMD], obj[MSG])


class Message:
    def __init__(self, command: int, data: str):
        self.command = command
        self.data = data

    def to_json(self):
        return dumps(self, cls=MessageEncoder)

    @staticmethod
    def from_json(data: bytes):
        try:
            return loads(data, cls=MessageDecoder)
        except:
            return None
