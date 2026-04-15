"""Aira SDK type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


# ─── Compliance framework constants ─────────────────────────────────
#
# String values accepted by :meth:`Aira.create_compliance_report` and
# returned on :class:`ComplianceReport.framework`. Importing these
# symbols (rather than hard-coding the strings) keeps callers in
# lockstep with the backend if a framework ever gets renamed.

FRAMEWORK_ART12 = "eu_ai_act_art12"
FRAMEWORK_ART9 = "eu_ai_act_art9"
FRAMEWORK_ART6 = "eu_ai_act_art6"
FRAMEWORK_ANNEX_IV = "eu_ai_act_annex_iv"


@dataclass
class Authorization:
    """Response from :meth:`Aira.authorize` — step 1 of the two-step flow.

    Status values:
    - ``"authorized"``: the agent may now execute the action, then call
      :meth:`Aira.notarize` with ``action_uuid`` to mint the receipt.
    - ``"pending_approval"``: the action is held for human review. The agent
      should not execute yet — wait for an approver to act, then poll
      :meth:`Aira.get_action` or handle the ``action.approved`` webhook.
    """

    action_uuid: str
    status: str  # "authorized" | "pending_approval"
    created_at: str
    request_id: str
    warnings: list[str] | None = None


@dataclass
class ActionReceipt:
    """Response from :meth:`Aira.notarize` — step 2 of the two-step flow.

    Status values:
    - ``"notarized"``: the action outcome was reported as ``"completed"`` and
      a cryptographic receipt has been minted. ``receipt_uuid``, ``payload_hash``,
      and ``signature`` are populated.
    - ``"failed"``: the action outcome was reported as ``"failed"``. No
      receipt is minted — signature/payload_hash/receipt_uuid will be ``None``.
    """

    action_uuid: str
    status: str  # "notarized" | "failed"
    created_at: str
    request_id: str
    receipt_uuid: str | None = None
    payload_hash: str | None = None
    signature: str | None = None
    timestamp_token: str | None = None
    # Output content-scan result attached at notarize time when the
    # org has an output policy enabled. ``None`` when output filtering
    # is off (global flag or per-org). Shape (subset):
    #     {"mode", "decision", "worst_severity", "libraries",
    #      "scanned_at", "hits": [{name, library, severity, matches, sample}]}
    output_scan_flags: dict | None = None
    warnings: list[str] | None = None


@dataclass
class OutputPolicy:
    """Per-org output content-scan policy.

    Returned by :meth:`Aira.get_output_policy` / updated via
    :meth:`Aira.update_output_policy`. ``mode`` is one of ``"flag"``
    (record-only), ``"deny"`` (refuse receipt on severe hit), or
    ``"redact"`` (hash the cleaned outcome).
    """

    enabled: bool
    mode: str
    libraries: list[str]
    deny_severity_threshold: str
    redact_severity_threshold: str
    request_id: str


@dataclass
class CosignResult:
    """Response from :meth:`Aira.cosign_action` — human co-signature on an action."""

    action_uuid: str
    cosigner_email: str
    cosigned_at: str
    cosignature_uuid: str
    request_id: str | None = None


@dataclass
class AuthorizationSummary:
    id: str
    authorizer_email: str
    authorized_at: str | None


@dataclass
class ReceiptSummary:
    receipt_uuid: str
    payload_hash: str
    signature: str
    public_key_id: str
    timestamp_token: str | None
    receipt_version: str
    verify_url: str
    created_at: str | None = None


@dataclass
class ActionDetail:
    action_uuid: str
    org_uuid: str
    action_type: str
    status: str
    legal_hold: bool
    action_details_hash: str
    created_at: str
    request_id: str
    agent_id: str | None = None
    agent_version: str | None = None
    instruction_hash: str | None = None
    details_storage_key: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    parent_action_uuid: str | None = None
    receipt: ReceiptSummary | None = None
    system_prompt_hash: str | None = None
    tool_inputs_hash: str | None = None
    model_params: dict | None = None
    execution_env: dict | None = None
    authorizations: list[AuthorizationSummary] = field(default_factory=list)


@dataclass
class AgentVersion:
    id: str
    version: str
    status: str
    created_at: str
    changelog: str | None = None
    model_id: str | None = None
    instruction_hash: str | None = None
    config_hash: str | None = None
    published_at: str | None = None


@dataclass
class AgentDetail:
    id: str
    agent_slug: str
    display_name: str
    status: str
    public: bool
    registered_at: str
    request_id: str
    description: str | None = None
    capabilities: list[str] | None = None
    metadata: dict | None = None
    versions: list[AgentVersion] = field(default_factory=list)


@dataclass
class EvidencePackage:
    id: str
    title: str
    action_uuids: list[str]
    package_hash: str
    signature: str
    status: str
    created_at: str
    request_id: str
    description: str | None = None
    agent_slugs: list[str] | None = None


@dataclass
class ComplianceSnapshot:
    id: str
    framework: str
    status: str
    findings: dict
    snapshot_hash: str
    signature: str
    snapshot_at: str
    created_at: str
    request_id: str
    agent_id: str | None = None


@dataclass
class EscrowTransaction:
    id: str
    transaction_type: str
    amount: str
    currency: str
    transaction_hash: str
    signature: str
    status: str
    created_at: str
    description: str | None = None
    reference_action_uuid: str | None = None


@dataclass
class EscrowAccount:
    id: str
    currency: str
    balance: str
    status: str
    created_at: str
    request_id: str
    agent_id: str | None = None
    counterparty_org_uuid: str | None = None
    purpose: str | None = None
    transactions: list[EscrowTransaction] = field(default_factory=list)


@dataclass
class VerifyResult:
    """Result of a public action receipt verification.

    The endpoint actually recomputes the SHA-256 hash and verifies the
    Ed25519 signature against the published public key — ``valid`` is the
    result of that real cryptographic check, not just an existence check.

    On a successful (or tamper-detected) verification the result includes
    the full evidence — ``signature``, ``public_key``, ``signed_payload``,
    ``timestamp_token`` — so an external auditor can re-run the same check
    with OpenSSL or any Ed25519 library without trusting Aira's verdict.
    """
    valid: bool
    public_key_id: str
    message: str
    verified_at: str
    request_id: str
    receipt_uuid: str | None = None
    action_uuid: str | None = None
    payload_hash: str | None = None
    signature: str | None = None
    public_key: str | None = None
    algorithm: str | None = None
    timestamp_token: str | None = None
    signed_payload: dict | None = None
    policy_evaluator_attestation: dict | None = None


@dataclass
class PaginatedList:
    data: list[dict]
    total: int
    page: int
    per_page: int
    has_more: bool


# ─── Compliance reports (Article 12 / 9 / 6) ─────────────────────────


@dataclass
class ComplianceReport:
    """A generated regulatory PDF report.

    Returned by :meth:`Aira.create_compliance_report`,
    :meth:`Aira.get_compliance_report`, and listed by
    :meth:`Aira.list_compliance_reports`. The PDF bytes are not included
    in this object — fetch them via :meth:`Aira.download_compliance_report`.
    """

    id: str
    framework: str
    status: str  # "pending" | "generating" | "ready" | "failed"
    created_at: str
    request_id: str
    org_uuid: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    action_uuid: str | None = None
    agent_filter: list[str] | None = None
    receipt_count: int | None = None
    pdf_size_bytes: int | None = None
    content_hash: str | None = None
    signature: str | None = None
    signing_key_id: str | None = None
    timestamp_token: str | None = None
    timestamp_token_present: bool = False
    report_metadata: dict | None = None
    error_message: str | None = None
    generated_at: str | None = None


@dataclass
class ComplianceReportVerification:
    """Result of :meth:`Aira.verify_compliance_report`."""

    report_uuid: str
    valid: bool
    checks: dict
    request_id: str
    descriptor: dict | None = None


@dataclass
class ActionExplanation:
    """Article 6 right-to-explanation for a single action.

    The response includes a cryptographic ``envelope`` — an Ed25519
    signature over the canonical JSON of every field above except the
    envelope itself and ``request_id``. Verify it offline against the
    public JWKS, or POST the full explanation (including ``envelope``)
    to :meth:`Aira.verify_action_explanation`.
    """

    action: dict
    policy_chain: list[dict]
    approval_chain: list[dict]
    regulation: dict
    request_id: str
    receipt: dict | None = None
    envelope: dict | None = None


@dataclass
class ExplanationVerification:
    """Result of :meth:`Aira.verify_action_explanation`.

    ``valid`` is true iff every entry in ``checks`` passed. Each check
    is either ``True`` or a string explaining the specific failure
    (missing envelope, unknown key, hash mismatch, bad signature).
    """

    valid: bool
    checks: dict
    request_id: str
    signing_key_id: str | None = None
