from pydantic import BaseModel
from typing import List


class OutputModel(BaseModel):
    """Structured result from the MQL agent containing file, compilation, and diagnostics."""

    script_type: str
    mql_version: str
    file_path: str
    compilation_log: str
    errors: List[str] = []
    warnings: List[str] = []
