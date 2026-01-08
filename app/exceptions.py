from fastapi import HTTPException

class ExternalServiceError(HTTPException):
    def __init__(self):
        super().__init__(status_code=503, detail="External LLM service unavailable")
