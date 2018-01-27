import abc


class MinecraftCommandsParser(abc.ABC):
    @abc.abstractmethod
    def parse(self, raw): ...
