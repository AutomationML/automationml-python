"""Exception types raised by the AutomationML SDK."""


class AutomationMLError(Exception):
    """Base class for SDK-specific errors."""


class CAEXValidationError(ValueError, AutomationMLError):
    """Raised when a CAEX document violates strict CAEX/XSD rules."""
