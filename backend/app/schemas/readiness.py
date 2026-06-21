from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from backend.app.schemas.documents import StrictBaseModel
from backend.app.schemas.enums import AccessLevel, PolicyType


class SimulatedPersona(StrictBaseModel):
    persona_id: str = Field(min_length=3, max_length=80)
    display_name: str = Field(min_length=3, max_length=120)
    department: str = Field(min_length=2, max_length=120)
    regions: list[str] = Field(min_length=1, max_length=20)
    max_access_level: AccessLevel
    allowed_policy_types: list[PolicyType] = Field(min_length=1, max_length=20)
    description: str = Field(min_length=10, max_length=500)

    @field_validator("persona_id", "display_name", "department", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field cannot be blank")
        return stripped

    @field_validator("regions")
    @classmethod
    def normalize_regions(cls, value: list[str]) -> list[str]:
        return _dedupe_non_empty(value)


class PersonaListResponse(StrictBaseModel):
    request_id: str
    items: list[SimulatedPersona]


class ReadinessCapabilities(StrictBaseModel):
    access_policy_simulation: bool = True
    metadata_filter_generation: bool = True
    persona_explanations: bool = True
    local_first: bool = True


class CorpusMetadataDistributions(StrictBaseModel):
    departments: dict[str, int] = Field(default_factory=dict)
    regions: dict[str, int] = Field(default_factory=dict)
    policy_types: dict[str, int] = Field(default_factory=dict)
    owners: dict[str, int] = Field(default_factory=dict)
    access_levels: dict[str, int] = Field(default_factory=dict)


class ReadinessGraphStatus(StrictBaseModel):
    available: bool = False
    node_count: int = Field(default=0, ge=0)
    edge_count: int = Field(default=0, ge=0)


class ReadinessEvaluationStatus(StrictBaseModel):
    available: bool = False
    total_cases: int = Field(default=0, ge=0)
    passed_cases: int = Field(default=0, ge=0)
    pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class ReadinessGovernanceStatus(StrictBaseModel):
    available: bool = False
    feedback_count: int = Field(default=0, ge=0)
    review_status_breakdown: dict[str, int] = Field(default_factory=dict)


class ReadinessSummaryResponse(StrictBaseModel):
    request_id: str
    simulation_only: Literal[True] = True
    personas_count: int = Field(ge=0)
    access_levels: list[AccessLevel]
    readiness_capabilities: ReadinessCapabilities = Field(default_factory=ReadinessCapabilities)
    corpus_metadata_distributions: CorpusMetadataDistributions = Field(
        default_factory=CorpusMetadataDistributions
    )
    graph_status: ReadinessGraphStatus = Field(default_factory=ReadinessGraphStatus)
    evaluation_status: ReadinessEvaluationStatus = Field(default_factory=ReadinessEvaluationStatus)
    governance_status: ReadinessGovernanceStatus = Field(default_factory=ReadinessGovernanceStatus)
    non_goals: list[str] = Field(default_factory=list)


class AccessPolicyAllowedFilters(StrictBaseModel):
    departments: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    policy_types: list[str] = Field(default_factory=list)
    access_levels: list[AccessLevel] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)

    @field_validator("departments", "regions", "policy_types", "owners")
    @classmethod
    def normalize_string_filters(cls, value: list[str]) -> list[str]:
        return _dedupe_non_empty(value)


class AccessPolicyRequest(StrictBaseModel):
    persona_id: str = Field(min_length=3, max_length=80)
    requested_departments: list[str] | None = None
    requested_regions: list[str] | None = None
    requested_policy_types: list[PolicyType] | None = None
    requested_access_levels: list[AccessLevel] | None = None
    requested_owners: list[str] | None = None

    @field_validator(
        "requested_departments",
        "requested_regions",
        "requested_policy_types",
        "requested_access_levels",
        "requested_owners",
        mode="before",
    )
    @classmethod
    def normalize_optional_list(cls, value):
        if value is None:
            return None
        if not isinstance(value, list):
            return value
        normalized = _dedupe_non_empty([str(item) for item in value])
        return normalized or None

    @field_validator("persona_id")
    @classmethod
    def strip_persona_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("persona_id cannot be blank")
        return stripped


class AccessPolicyResponse(StrictBaseModel):
    request_id: str
    persona: SimulatedPersona
    allowed_filters: AccessPolicyAllowedFilters
    denied_reasons: list[str] = Field(default_factory=list)
    explanation: str
    simulation_only: Literal[True] = True


def _dedupe_non_empty(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        stripped = item.strip()
        if not stripped:
            continue
        key = stripped.casefold()
        if key not in seen:
            normalized.append(stripped)
            seen.add(key)
    return normalized
