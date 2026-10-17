"""Exception types raised by the AutomationML SDK."""


class AutomationMLError(Exception):
    """Base class for SDK-specific errors."""


class CAEXValidationError(ValueError, AutomationMLError):
    """Raised when a CAEX document violates strict CAEX/XSD rules."""


class ReferenceNotFoundError(LookupError, AutomationMLError):
    """Raised when a required ID or CAEX path cannot be resolved."""


class AmbiguousReferenceError(LookupError, AutomationMLError):
    """Raised when a supposedly unique ID or CAEX path has multiple targets."""


class LegacyConversionWarning(UserWarning):
    """Warns that CAEX 2.15 input was automatically upgraded to CAEX 3.0."""


class LegacyConversionError(ValueError, AutomationMLError):
    """Raised when CAEX 2.15 cannot be upgraded without data loss."""


class AMLParseError(LegacyConversionError):
    """Raised when AML XML is not a readable CAEX 2.15 or CAEX 3.0 document.

    It subclasses ``LegacyConversionError``, which earlier versions raised for
    the same input, so existing handlers keep working.
    """


class MissingDependencyError(ModuleNotFoundError, AutomationMLError):
    """Raised when an optional feature is used without its extra installed."""

    def __init__(self, feature: str, module: str, extra: str) -> None:
        super().__init__(
            f"{feature} needs the optional dependency {module!r}. Install it with: "
            f'python -m pip install "automationml[{extra}]"',
            name=module,
        )


class ChangeSetError(ValueError, AutomationMLError):
    """Raised when a document change set is invalid or targets the wrong base."""
