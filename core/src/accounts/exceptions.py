from django.core.exceptions import ValidationError


class PhoneConflictError(ValidationError):
    """A phone was claimed after allauth's form-level ownership check."""
