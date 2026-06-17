---
doc_id: it-incident-escalation-sop-v1-0
title: IT Incident Escalation SOP
department: IT
regions:
  - Global
policy_type: sop
effective_date: "2025-03-01"
version: "1.0"
access_level: restricted
owner: IT Service Management
related_processes:
  - IT Incident Management
created_at: "2025-01-01T00:00:00Z"
updated_at: "2025-03-01T00:00:00Z"
---
# IT Incident Escalation SOP

## Purpose and Scope

This SOP defines how IT incidents are classified, acknowledged, escalated, and recorded. It applies to incidents reported through ServiceNow, the IT Service Desk, or automated monitoring.

IT Service Management owns this SOP. The Information Security team participates when an incident may involve data exposure, account compromise, or malware.

## Severity Levels

Severity 1 incidents are critical incidents that cause a major business outage, confirmed security compromise, or material data-risk event. Severity 1 incidents must be acknowledged within 15 minutes.

Severity 2 incidents affect a business-critical service for a limited user group. Severity 3 incidents are standard support incidents with limited impact.

## Severity 1 Workflow

The IT Service Desk logs the incident in ServiceNow and assigns Severity 1 when the criteria are met. The desk must notify the Incident Commander and the Information Security duty lead within 15 minutes.

The Incident Commander opens a bridge, coordinates technical responders, and records material decisions in the ServiceNow incident record.

## Escalation Path

If customer data, employee data, or confidential company information may be exposed, the Information Security duty lead escalates to the Data Protection Office.

If the incident remains unresolved after 60 minutes, the Incident Commander escalates to the CIO delegate and provides an impact summary.

## Closure Requirements

The Incident Commander may close a Severity 1 incident only after service restoration, stakeholder notification, and completion of an initial root-cause note in ServiceNow.

A post-incident review must be scheduled within 5 business days.

