from typing import Optional


class DictRepr:
    def __str__(self) -> str:
        return self.dict_repr() or self.id_repr()

    def __repr__(self) -> str:
        return str(self)

    def dict_repr(self) -> Optional[str]:
        params = {k: getattr(self, k) for k in self.__dict__}
        pairs = (f"{k}={v!r}" for k, v in params.items())
        return "".join((f"{self.__class__.__name__}(", ", ".join(pairs), ")"))

    def id_repr(self) -> str:
        return f"<{self.__class__.__name__} #{id(self)}>"
