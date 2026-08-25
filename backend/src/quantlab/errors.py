class DataUnavailableError(RuntimeError):
    def __init__(self, code: str, attempts: int):
        self.code = code
        self.attempts = attempts
        super().__init__(f"Data unavailable for {code} after {attempts} attempts")


class InstrumentNotFoundError(LookupError):
    def __init__(self, code_or_query: str):
        self.code_or_query = code_or_query
        super().__init__(f"未找到证券：{code_or_query}")
