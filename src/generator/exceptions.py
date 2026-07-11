"""
Standardized exception hierarchy for personetta.

Provides consistent error handling across loader, merger, validator, and CLI.
"""


class PersonettaError(Exception):
    """Base exception for all personetta errors."""

    pass


class LoadError(PersonettaError):
    """Error loading YAML files, roles, or recipes."""

    pass


class ValidationError(PersonettaError):
    """Error validating recipe structure or content."""

    pass


class CompositionError(PersonettaError):
    """Error composing recipes from roles and mixins."""

    pass


class InstallationError(PersonettaError):
    """Error installing recipes to target directories."""

    pass


class PipelineError(PersonettaError):
    """Error executing work pipeline."""

    pass
