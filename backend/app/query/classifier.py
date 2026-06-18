from __future__ import annotations

import re

from .schema import QueryIntent


class RuleBasedQueryClassifier:
    """Deterministic Phase 5A classifier. It plans evidence routes only."""

    OUT_OF_SCOPE_TERMS = {
        "capital of",
        "president of",
        "weather",
        "stock",
        "share price",
        "restaurant",
        "recipe",
        "movie",
        "sports",
        "football",
        "basketball",
        "joke",
        "poem",
        "python function",
        "reverse a string",
        "dating",
        "medical diagnosis",
        "legal advice",
    }
    UNSUPPORTED_TERMS = {
        "write the final answer",
        "generate the final answer",
        "draft the final answer",
        "compose an answer",
        "write a response",
        "draft a response",
        "summarize the answer",
        "make a recommendation",
    }
    GRAPH_TERMS = {
        "graph",
        "node",
        "edge",
        "relation",
        "relationship",
        "relationships",
        "neighborhood",
        "connected",
        "links",
        "linked",
        "entity",
        "entities",
    }
    MULTI_HOP_TERMS = {
        "multi-hop",
        "multi hop",
        "depends on",
        "relationship between",
        "between",
        "who approves",
        "who owns",
        "who escalates",
        "escalates to",
        "requires approval",
        "approval path",
        "approval chain",
    }
    PROCESS_TERMS = {
        "process",
        "workflow",
        "sop",
        "steps",
        "procedure",
        "escalation",
        "incident",
        "onboarding",
        "complaint",
        "service now",
        "servicenow",
    }
    POLICY_TERMS = {
        "policy",
        "rule",
        "requirement",
        "requires",
        "required",
        "approval",
        "form",
        "threshold",
        "reimbursement",
        "payment",
        "leave",
        "data",
        "cross-border",
        "confidential",
        "restricted",
    }
    ENTERPRISE_DOMAIN_TERMS = {
        "access level",
        "ai tool usage",
        "ai tools",
        "apac",
        "approval",
        "capital expenditure",
        "concur",
        "confidential",
        "cross-border",
        "customer complaint",
        "data handling",
        "data security",
        "dpo",
        "employee",
        "eu",
        "finance",
        "form",
        "hr",
        "hris",
        "incident",
        "it",
        "knowledgeops",
        "leave",
        "northstar",
        "onboarding",
        "owner",
        "ownership",
        "payment",
        "policy",
        "procurement",
        "process",
        "reimbursement",
        "restricted",
        "servicenow",
        "service now",
        "sop",
        "threshold",
        "travel",
        "vendor",
        "workday",
    }

    def classify(self, query: str) -> QueryIntent:
        normalized = normalize_query(query)
        if not normalized:
            return QueryIntent.UNSUPPORTED
        if contains_any(normalized, self.OUT_OF_SCOPE_TERMS):
            return QueryIntent.OUT_OF_SCOPE
        if not contains_any(normalized, self.ENTERPRISE_DOMAIN_TERMS):
            return QueryIntent.OUT_OF_SCOPE
        if contains_any(normalized, self.UNSUPPORTED_TERMS):
            return QueryIntent.UNSUPPORTED
        if contains_any(normalized, self.GRAPH_TERMS):
            return QueryIntent.GRAPH_EXPLORATION
        if contains_any(normalized, self.MULTI_HOP_TERMS):
            return QueryIntent.MULTI_HOP
        if contains_any(normalized, self.PROCESS_TERMS):
            return QueryIntent.PROCESS_LOOKUP
        if contains_any(normalized, self.POLICY_TERMS):
            return QueryIntent.POLICY_LOOKUP
        return QueryIntent.FACT_LOOKUP


def normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().casefold())


def contains_any(value: str, terms: set[str]) -> bool:
    return any(term in value for term in terms)
