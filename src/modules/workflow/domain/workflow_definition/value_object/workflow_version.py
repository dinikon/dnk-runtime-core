from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowVersionVO:
    """Workflow version label."""

    value: str

    @classmethod
    def draft(cls) -> "WorkflowVersionVO":
        """Creates the draft workflow definition version."""
        return cls("draft")


__all__ = ["WorkflowVersionVO"]
