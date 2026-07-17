from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from fr_harness.config import ApprovalSettings
from fr_harness.models import Action, ActionKind, ApprovalDecision


class GuardDecision(StrEnum):
    ALLOWED = "allowed"
    REQUIRES_APPROVAL = "requires_approval"
    BLOCKED = "blocked"


@dataclass
class Approval:
    id: UUID
    kind: str
    description: str
    decision: ApprovalDecision = ApprovalDecision.PENDING


def resolve_workspace_path(root: Path, value: str) -> Path:
    resolved_root = root.resolve()
    resolved_path = (resolved_root / value).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise ValueError("outside workspace")
    return resolved_path


def classify(
    action: Action,
    root: Path,
    policy: ApprovalSettings | None = None,
) -> GuardDecision:
    active_policy = policy or ApprovalSettings()
    if action.path is not None:
        try:
            target = resolve_workspace_path(root, action.path)
        except ValueError:
            return GuardDecision.BLOCKED
        if action.kind is ActionKind.WRITE_FILE:
            if target.exists() and active_policy.existing_file_write:
                return GuardDecision.REQUIRES_APPROVAL
            return GuardDecision.ALLOWED
    if action.kind is ActionKind.RUN_PYTEST and active_policy.run_pytest:
        return GuardDecision.REQUIRES_APPROVAL
    return GuardDecision.ALLOWED


class ApprovalStateMachine:
    def __init__(self) -> None:
        self._approvals: dict[UUID, Approval] = {}

    def create(self, kind: str, description: str) -> Approval:
        approval = Approval(id=uuid4(), kind=kind, description=description)
        self._approvals[approval.id] = approval
        return approval

    def approve(self, approval_id: UUID) -> None:
        self._get_pending(approval_id).decision = ApprovalDecision.APPROVED

    def reject(self, approval_id: UUID) -> None:
        self._get_pending(approval_id).decision = ApprovalDecision.REJECTED

    def can_execute(self, approval_id: UUID) -> bool:
        return self._get(approval_id).decision is ApprovalDecision.APPROVED

    def consume(self, approval_id: UUID) -> bool:
        approval = self._get(approval_id)
        if approval.decision is not ApprovalDecision.APPROVED:
            return False
        approval.decision = ApprovalDecision.CONSUMED
        return True

    def _get(self, approval_id: UUID) -> Approval:
        try:
            return self._approvals[approval_id]
        except KeyError as error:
            raise KeyError(f"unknown approval: {approval_id}") from error

    def _get_pending(self, approval_id: UUID) -> Approval:
        approval = self._get(approval_id)
        if approval.decision is not ApprovalDecision.PENDING:
            raise ValueError(f"approval is no longer pending: {approval_id}")
        return approval
