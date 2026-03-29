"""
Shared Application — Cross-cutting application concerns.

Contains:
- Result type for functional error handling
- Command/Query base classes (CQRS)
"""

from tacto.shared.application.result import (
    Err,
    Failure,
    Ok,
    Result,
    ResultUtils,
    Success,
)

__all__ = [
    "Result",
    "Success",
    "Failure",
    "ResultUtils",
    "Ok",
    "Err",
]
