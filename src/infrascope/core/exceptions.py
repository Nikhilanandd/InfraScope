class InfraScopeError(Exception):
    """Base exception for InfraScope."""

class CollectorError(InfraScopeError):
    """Raised when a hardware collector fails."""

class DependencyError(InfraScopeError):
    """Raised when a required dependency is missing."""

class BenchmarkError(InfraScopeError):
    """Raised when benchmarking fails."""

class ReportError(InfraScopeError):
    """Raised when report generation fails."""

class PermissionError_(InfraScopeError):
    """Raised when permission is denied."""
