class VideoGenError(Exception):
    """Base error safe to show to a CLI user."""


class PolicyError(VideoGenError):
    """A fail-closed project policy rejected an operation."""


class BudgetExceeded(PolicyError):
    """A reservation would exceed the selected budget."""


class ProviderError(VideoGenError):
    """The provider returned an invalid or failed response."""


class UnknownBillingStatus(ProviderError):
    """A request may have been billed and must be reconciled manually."""

