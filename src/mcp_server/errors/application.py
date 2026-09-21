class WellnessAPIError(Exception):
    """Safe application error raised for upstream KTO API failures."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")