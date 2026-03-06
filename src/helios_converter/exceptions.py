class ConversionError(Exception):
    """Raised when the agent fails to complete a conversion run."""

    def __init__(self, message: str, cause: BaseException | None = None) -> None:
        location = ""
        if cause is not None:
            tb = cause.__traceback__
            while tb is not None and tb.tb_next is not None:
                tb = tb.tb_next
            if tb is not None:
                location = f" (at {tb.tb_frame.f_code.co_filename}:{tb.tb_lineno})"
        super().__init__(f"{message}{location}")
        if cause is not None:
            self.__cause__ = cause
