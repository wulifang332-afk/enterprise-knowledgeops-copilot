from __future__ import annotations

import pytest

from backend.app.core.errors import KnowledgeOpsError
from backend.app.readiness.access_policy import AccessPolicyEngine, access_level_rank, access_levels_up_to
from backend.app.schemas.enums import AccessLevel
from backend.app.schemas.readiness import AccessPolicyRequest


PERSONA_IDS = [
    "global_admin",
    "finance_manager_apac",
    "hr_manager_eu",
    "it_support_internal",
    "legal_reviewer_global",
    "employee_public",
]


def test_phase9b_persona_lookup_returns_deterministic_personas() -> None:
    engine = AccessPolicyEngine()

    personas = engine.personas()

    assert [persona.persona_id for persona in personas] == PERSONA_IDS
    assert engine.persona_for("finance_manager_apac").department == "Finance"
    assert engine.persona_for("employee_public").max_access_level == AccessLevel.PUBLIC
    with pytest.raises(KnowledgeOpsError) as exc_info:
        engine.persona_for("unknown_persona")
    assert exc_info.value.error_code == "INVALID_REQUEST"


def test_phase9b_access_level_ordering_is_deterministic() -> None:
    assert access_level_rank(AccessLevel.PUBLIC) < access_level_rank(AccessLevel.INTERNAL)
    assert access_level_rank(AccessLevel.INTERNAL) < access_level_rank(AccessLevel.RESTRICTED)
    assert access_level_rank(AccessLevel.RESTRICTED) < access_level_rank(AccessLevel.CONFIDENTIAL)
    assert access_levels_up_to(AccessLevel.RESTRICTED) == [
        AccessLevel.PUBLIC,
        AccessLevel.INTERNAL,
        AccessLevel.RESTRICTED,
    ]


def test_phase9b_default_filters_are_generated_for_each_persona() -> None:
    engine = AccessPolicyEngine()
    expected_departments = {
        "global_admin": [],
        "finance_manager_apac": ["Finance"],
        "hr_manager_eu": ["Human Resources"],
        "it_support_internal": ["IT", "Information Security"],
        "legal_reviewer_global": [],
        "employee_public": [],
    }

    for persona_id in PERSONA_IDS:
        response = engine.simulate(AccessPolicyRequest(persona_id=persona_id), request_id="unit")
        persona = response.persona

        assert response.simulation_only is True
        assert response.denied_reasons == []
        assert response.allowed_filters.departments == expected_departments[persona_id]
        assert response.allowed_filters.regions == persona.regions
        assert response.allowed_filters.policy_types == [item.value for item in persona.allowed_policy_types]
        assert response.allowed_filters.access_levels == access_levels_up_to(persona.max_access_level)
        assert "simulation-only" in response.explanation


def test_phase9b_requested_filters_intersect_with_persona_scope() -> None:
    engine = AccessPolicyEngine()

    response = engine.simulate(
        AccessPolicyRequest(
            persona_id="finance_manager_apac",
            requested_departments=["Finance", "Human Resources"],
            requested_regions=["APAC", "EU"],
            requested_policy_types=["policy", "manual"],
            requested_access_levels=["internal", "confidential"],
            requested_owners=["Finance Operations", "Data Protection Office"],
        ),
        request_id="unit",
    )

    assert response.allowed_filters.departments == ["Finance"]
    assert response.allowed_filters.regions == ["APAC"]
    assert response.allowed_filters.policy_types == ["policy"]
    assert response.allowed_filters.access_levels == [AccessLevel.INTERNAL]
    assert response.allowed_filters.owners == ["Finance Operations"]
    assert response.denied_reasons == [
        "requested_departments denied outside persona scope: Human Resources",
        "requested_regions denied outside persona scope: EU",
        "requested_policy_types denied outside persona scope: manual",
        "requested_access_levels denied above max_access_level restricted: confidential",
        "requested_owners denied outside persona scope: Data Protection Office",
    ]


def test_phase9b_all_denied_requested_filters_return_empty_allowed_lists() -> None:
    engine = AccessPolicyEngine()

    response = engine.simulate(
        AccessPolicyRequest(
            persona_id="finance_manager_apac",
            requested_departments=["Human Resources"],
            requested_regions=["EU"],
            requested_policy_types=["manual"],
            requested_access_levels=["confidential"],
            requested_owners=["Data Protection Office"],
        ),
        request_id="unit",
    )

    assert response.allowed_filters.departments == []
    assert response.allowed_filters.regions == []
    assert response.allowed_filters.policy_types == []
    assert response.allowed_filters.access_levels == []
    assert response.allowed_filters.owners == []
    assert len(response.denied_reasons) == 5
    assert "outside the persona scope were denied" in response.explanation
