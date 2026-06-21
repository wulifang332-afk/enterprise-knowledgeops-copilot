from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from backend.app.core.errors import KnowledgeOpsError
from backend.app.schemas.enums import AccessLevel, ErrorCode, PolicyType
from backend.app.schemas.readiness import (
    AccessPolicyAllowedFilters,
    AccessPolicyRequest,
    AccessPolicyResponse,
    SimulatedPersona,
)


ACCESS_LEVEL_ORDER: tuple[AccessLevel, ...] = (
    AccessLevel.PUBLIC,
    AccessLevel.INTERNAL,
    AccessLevel.RESTRICTED,
    AccessLevel.CONFIDENTIAL,
)


@dataclass(frozen=True)
class PersonaPolicy:
    persona: SimulatedPersona
    department_scope: tuple[str, ...] | None = None
    owner_scope: tuple[str, ...] | None = None


class AccessPolicyEngine:
    def __init__(self) -> None:
        self._policies = _build_persona_policies()

    def personas(self) -> list[SimulatedPersona]:
        return [policy.persona for policy in self._policies.values()]

    def persona_for(self, persona_id: str) -> SimulatedPersona:
        return self._profile_for(persona_id).persona

    def simulate(self, request: AccessPolicyRequest, *, request_id: str) -> AccessPolicyResponse:
        profile = self._profile_for(request.persona_id)
        denied_reasons: list[str] = []

        allowed_filters = AccessPolicyAllowedFilters(
            departments=self._resolve_string_scope(
                field_name="requested_departments",
                requested=request.requested_departments,
                scope=profile.department_scope,
                denied_reasons=denied_reasons,
            ),
            regions=self._resolve_string_scope(
                field_name="requested_regions",
                requested=request.requested_regions,
                scope=tuple(profile.persona.regions),
                denied_reasons=denied_reasons,
            ),
            policy_types=self._resolve_string_scope(
                field_name="requested_policy_types",
                requested=[item.value for item in request.requested_policy_types]
                if request.requested_policy_types
                else None,
                scope=tuple(item.value for item in profile.persona.allowed_policy_types),
                denied_reasons=denied_reasons,
            ),
            access_levels=self._resolve_access_levels(
                max_access_level=profile.persona.max_access_level,
                requested=request.requested_access_levels,
                denied_reasons=denied_reasons,
            ),
            owners=self._resolve_string_scope(
                field_name="requested_owners",
                requested=request.requested_owners,
                scope=profile.owner_scope,
                denied_reasons=denied_reasons,
            ),
        )

        return AccessPolicyResponse(
            request_id=request_id,
            persona=profile.persona,
            allowed_filters=allowed_filters,
            denied_reasons=denied_reasons,
            explanation=_build_explanation(profile.persona, denied_reasons),
            simulation_only=True,
        )

    def _profile_for(self, persona_id: str) -> PersonaPolicy:
        key = persona_id.strip()
        if key not in self._policies:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_REQUEST,
                "Unknown simulated persona.",
                {"persona_id": persona_id},
            )
        return self._policies[key]

    @staticmethod
    def _resolve_string_scope(
        *,
        field_name: str,
        requested: list[str] | None,
        scope: tuple[str, ...] | None,
        denied_reasons: list[str],
    ) -> list[str]:
        if scope is None:
            return list(requested or [])
        if not requested:
            return list(scope)

        scope_by_key = {item.casefold(): item for item in scope}
        allowed: list[str] = []
        denied: list[str] = []
        for value in requested:
            canonical = scope_by_key.get(value.casefold())
            if canonical is None:
                denied.append(value)
            elif canonical not in allowed:
                allowed.append(canonical)
        if denied:
            denied_reasons.append(
                f"{field_name} denied outside persona scope: {', '.join(denied)}"
            )
        return allowed

    @staticmethod
    def _resolve_access_levels(
        *,
        max_access_level: AccessLevel,
        requested: list[AccessLevel] | None,
        denied_reasons: list[str],
    ) -> list[AccessLevel]:
        allowed_scope = access_levels_up_to(max_access_level)
        if not requested:
            return allowed_scope

        allowed: list[AccessLevel] = []
        denied: list[AccessLevel] = []
        for level in requested:
            if access_level_rank(level) <= access_level_rank(max_access_level):
                if level not in allowed:
                    allowed.append(level)
            else:
                denied.append(level)
        if denied:
            denied_reasons.append(
                "requested_access_levels denied above max_access_level "
                f"{max_access_level.value}: {', '.join(level.value for level in denied)}"
            )
        return allowed


def access_level_rank(level: AccessLevel) -> int:
    return ACCESS_LEVEL_ORDER.index(level)


def access_levels_up_to(max_access_level: AccessLevel) -> list[AccessLevel]:
    max_rank = access_level_rank(max_access_level)
    return [level for level in ACCESS_LEVEL_ORDER if access_level_rank(level) <= max_rank]


def _build_explanation(persona: SimulatedPersona, denied_reasons: list[str]) -> str:
    base = (
        f"{persona.display_name} is simulated with department '{persona.department}', "
        f"regions {', '.join(persona.regions)}, and max_access_level "
        f"'{persona.max_access_level.value}'. The response is simulation-only and produces "
        "metadata filters for later pre-retrieval use."
    )
    if denied_reasons:
        return f"{base} Requested filters outside the persona scope were denied."
    return f"{base} All requested filters are within persona scope."


def _persona(
    *,
    persona_id: str,
    display_name: str,
    department: str,
    regions: list[str],
    max_access_level: AccessLevel,
    allowed_policy_types: Iterable[PolicyType],
    description: str,
) -> SimulatedPersona:
    return SimulatedPersona(
        persona_id=persona_id,
        display_name=display_name,
        department=department,
        regions=regions,
        max_access_level=max_access_level,
        allowed_policy_types=list(allowed_policy_types),
        description=description,
    )


def _build_persona_policies() -> dict[str, PersonaPolicy]:
    all_policy_types = tuple(PolicyType)
    policies = [
        PersonaPolicy(
            persona=_persona(
                persona_id="global_admin",
                display_name="Global Admin",
                department="Enterprise Administration",
                regions=["Global", "APAC", "EU"],
                max_access_level=AccessLevel.CONFIDENTIAL,
                allowed_policy_types=all_policy_types,
                description="Portfolio simulation persona with global metadata visibility across the local corpus.",
            ),
            department_scope=None,
            owner_scope=None,
        ),
        PersonaPolicy(
            persona=_persona(
                persona_id="finance_manager_apac",
                display_name="Finance Manager APAC",
                department="Finance",
                regions=["APAC", "Global"],
                max_access_level=AccessLevel.RESTRICTED,
                allowed_policy_types=[
                    PolicyType.POLICY,
                    PolicyType.SOP,
                    PolicyType.STANDARD,
                    PolicyType.GUIDELINE,
                    PolicyType.FORM,
                ],
                description="Simulates an APAC finance manager viewing finance-owned policies and procedures.",
            ),
            department_scope=("Finance",),
            owner_scope=("Finance Operations",),
        ),
        PersonaPolicy(
            persona=_persona(
                persona_id="hr_manager_eu",
                display_name="HR Manager EU",
                department="Human Resources",
                regions=["EU", "Global"],
                max_access_level=AccessLevel.RESTRICTED,
                allowed_policy_types=[
                    PolicyType.POLICY,
                    PolicyType.SOP,
                    PolicyType.GUIDELINE,
                    PolicyType.FORM,
                    PolicyType.MANUAL,
                ],
                description="Simulates an EU HR manager viewing HR-owned employee policy and SOP material.",
            ),
            department_scope=("Human Resources",),
            owner_scope=("Human Resources Operations",),
        ),
        PersonaPolicy(
            persona=_persona(
                persona_id="it_support_internal",
                display_name="IT Support Internal",
                department="IT",
                regions=["Global"],
                max_access_level=AccessLevel.RESTRICTED,
                allowed_policy_types=[
                    PolicyType.SOP,
                    PolicyType.STANDARD,
                    PolicyType.MANUAL,
                    PolicyType.GUIDELINE,
                ],
                description="Simulates an internal IT support persona for operational support procedures.",
            ),
            department_scope=("IT", "Information Security"),
            owner_scope=("IT Service Management", "Information Security"),
        ),
        PersonaPolicy(
            persona=_persona(
                persona_id="legal_reviewer_global",
                display_name="Legal Reviewer Global",
                department="Legal and Compliance",
                regions=["Global", "APAC", "EU"],
                max_access_level=AccessLevel.CONFIDENTIAL,
                allowed_policy_types=all_policy_types,
                description="Simulates a global legal reviewer with confidential policy review visibility.",
            ),
            department_scope=None,
            owner_scope=None,
        ),
        PersonaPolicy(
            persona=_persona(
                persona_id="employee_public",
                display_name="Employee Public",
                department="General Employee",
                regions=["Global"],
                max_access_level=AccessLevel.PUBLIC,
                allowed_policy_types=[PolicyType.POLICY, PolicyType.GUIDELINE, PolicyType.FORM],
                description="Simulates a general employee restricted to public-facing policy metadata.",
            ),
            department_scope=None,
            owner_scope=None,
        ),
    ]
    return {policy.persona.persona_id: policy for policy in policies}
