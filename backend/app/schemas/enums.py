from __future__ import annotations

from enum import StrEnum


class AccessLevel(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    CONFIDENTIAL = "confidential"


class PolicyType(StrEnum):
    POLICY = "policy"
    SOP = "sop"
    STANDARD = "standard"
    GUIDELINE = "guideline"
    FORM = "form"
    MANUAL = "manual"


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_METADATA = "INVALID_METADATA"
    INVALID_FILE_PATH = "INVALID_FILE_PATH"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    DUPLICATE_DOCUMENT = "DUPLICATE_DOCUMENT"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    INDEX_UNAVAILABLE = "INDEX_UNAVAILABLE"
    EMBEDDING_PROVIDER_UNAVAILABLE = "EMBEDDING_PROVIDER_UNAVAILABLE"
    LLM_PROVIDER_UNAVAILABLE = "LLM_PROVIDER_UNAVAILABLE"
    GRAPH_UNAVAILABLE = "GRAPH_UNAVAILABLE"
    ACCESS_DENIED = "ACCESS_DENIED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CITATION_VALIDATION_FAILED = "CITATION_VALIDATION_FAILED"
    INVALID_EVALUATION_CASE = "INVALID_EVALUATION_CASE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AuditEventType(StrEnum):
    DOCUMENT_INGESTION = "document_ingestion"
    DOCUMENT_VALIDATION_FAILURE = "document_validation_failure"
    SEARCH_REQUEST = "search_request"
    QUERY_REQUEST = "query_request"
    ACCESS_DENIAL = "access_denial"
    ANSWER_GENERATION = "answer_generation"
    CITATION_VALIDATION_FAILURE = "citation_validation_failure"
    GRAPH_EXTRACTION = "graph_extraction"
    EVALUATION_RUN = "evaluation_run"
    FEEDBACK_SUBMISSION = "feedback_submission"
    FEEDBACK_STATUS_UPDATED = "feedback_status_updated"
    FEEDBACK_REVIEWER_NOTE_UPDATED = "feedback_reviewer_note_updated"
    FEEDBACK_EVAL_LINKED = "feedback_eval_linked"


class IngestionStatus(StrEnum):
    INGESTED = "ingested"
    SKIPPED = "skipped"
    FAILED = "failed"
