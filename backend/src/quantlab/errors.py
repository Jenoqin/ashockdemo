class DataUnavailableError(RuntimeError):
    def __init__(self, code: str, attempts: int):
        self.code = code
        self.attempts = attempts
        super().__init__(f"Data unavailable for {code} after {attempts} attempts")
