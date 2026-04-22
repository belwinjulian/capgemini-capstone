"""Synthetic patient-safety document generation.

Produces 100 templated documents across 4 types with weighted entity frequencies
chosen so the three demo questions have clear, verifiable answers:

  1. Top medications across adverse events -> heparin + insulin are seeded to dominate
  2. Recurring root causes across RCAs      -> inadequate_staffing + miscommunication_handoff dominate
  3. Departments central to sentinel events -> icu + er are seeded to be central
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from app.models import Document

SEED = 42

MEDICATIONS = [
    ("heparin", 6),
    ("insulin", 6),
    ("vancomycin", 3),
    ("morphine", 3),
    ("warfarin", 3),
    ("metformin", 1),
    ("furosemide", 1),
    ("lisinopril", 1),
    ("cefazolin", 1),
    ("oxycodone", 1),
]

DEPARTMENTS = [
    ("icu", 6),
    ("er", 6),
    ("or", 3),
    ("medical-surgical", 2),
    ("pediatrics", 2),
    ("cardiology", 2),
    ("oncology", 1),
    ("radiology", 1),
]

INCIDENT_TYPES = [
    "medication_error",
    "dosage_error",
    "wrong_site_surgery",
    "patient_fall",
    "hospital_acquired_infection",
    "diagnostic_error",
    "delayed_treatment",
    "specimen_mislabeling",
    "pressure_injury",
]

STAFF_ROLES = [
    "registered_nurse",
    "attending_physician",
    "pharmacist",
    "resident",
    "anesthesiologist",
    "respiratory_therapist",
]

ROOT_CAUSES = [
    ("inadequate_staffing", 6),
    ("miscommunication_handoff", 6),
    ("protocol_deviation", 4),
    ("knowledge_gap", 2),
    ("equipment_failure", 1),
    ("alarm_fatigue", 1),
    ("incomplete_documentation", 1),
]

PROTOCOLS = [
    "medication_reconciliation",
    "universal_protocol_time_out",
    "fall_prevention_bundle",
    "infection_prevention_bundle",
    "handoff_sbar",
]


def _weighted(options: list[tuple[str, int]]) -> list[str]:
    return [name for name, weight in options for _ in range(weight)]


def _pick(rng: random.Random, options: list[tuple[str, int]]) -> str:
    return rng.choice(_weighted(options))


def _aer(rng: random.Random, idx: int) -> Document:
    doc_id = f"AER-{idx:03d}"
    med = _pick(rng, MEDICATIONS)
    dept = _pick(rng, DEPARTMENTS)
    incident = rng.choice(INCIDENT_TYPES)
    staff = rng.choice(STAFF_ROLES)
    severity = rng.choice(["minor", "moderate", "serious", "sentinel"])
    report_date = date(2025, 1, 1) + timedelta(days=rng.randint(0, 365))
    body = (
        f"Adverse Event Report {doc_id}\n"
        f"Date of event: {report_date.isoformat()}\n"
        f"Severity: {severity}\n"
        f"Department: {dept.upper()}\n\n"
        f"SUMMARY\n"
        f"A {incident.replace('_', ' ')} occurred in the {dept.upper()} involving the medication "
        f"{med}. The event was first identified by a {staff.replace('_', ' ')} during routine "
        f"patient assessment. Initial investigation indicates the event was classified as "
        f"{severity}.\n\n"
        f"NARRATIVE\n"
        f"The patient was receiving {med} per the standing order when the {staff.replace('_', ' ')} "
        f"noted a discrepancy between the charted dose and the medication administration record. "
        f"The {staff.replace('_', ' ')} escalated the concern to the attending physician. "
        f"Standard {rng.choice(PROTOCOLS).replace('_', ' ')} steps were reviewed. "
        f"No permanent harm was identified; the patient remained stable throughout the shift.\n\n"
        f"CONTRIBUTING FACTORS\n"
        f"- {_pick(rng, ROOT_CAUSES).replace('_', ' ')}\n"
        f"- {_pick(rng, ROOT_CAUSES).replace('_', ' ')}\n\n"
        f"FOLLOW-UP\n"
        f"Case referred for RCA review. {med.title()} administration workflow in the "
        f"{dept.upper()} will be re-audited within 30 days."
    )
    return Document(
        doc_id=doc_id,
        doc_type="adverse_event",
        title=f"Adverse Event Report {doc_id}: {incident.replace('_', ' ')} in {dept.upper()}",
        content=body,
        metadata={
            "severity": severity,
            "event_date": report_date.isoformat(),
            "primary_medication": med,
            "primary_department": dept,
            "incident_type": incident,
        },
    )


def _rca(rng: random.Random, idx: int) -> Document:
    doc_id = f"RCA-{idx:03d}"
    dept = _pick(rng, DEPARTMENTS)
    incident = rng.choice(INCIDENT_TYPES)
    root_causes = list(
        dict.fromkeys([_pick(rng, ROOT_CAUSES) for _ in range(rng.randint(2, 4))])
    )
    contributing_med = _pick(rng, MEDICATIONS)
    body = (
        f"Root Cause Analysis {doc_id}\n"
        f"Incident reviewed: {incident.replace('_', ' ')} in the {dept.upper()}.\n"
        f"Involved medication (where applicable): {contributing_med}.\n\n"
        f"METHODOLOGY\n"
        f"A multidisciplinary RCA team convened within 72 hours of the event. The team applied "
        f"the five whys technique and mapped the event timeline against the "
        f"{rng.choice(PROTOCOLS).replace('_', ' ')} protocol.\n\n"
        f"ROOT CAUSES IDENTIFIED\n"
        + "\n".join(f"- {rc.replace('_', ' ')}" for rc in root_causes)
        + "\n\nCONTRIBUTING FACTORS\n"
        f"- Variability in {dept.upper()} staff-to-patient ratios during night shift\n"
        f"- Incomplete handoff from prior shift\n\n"
        f"ACTIONS\n"
        f"- Reinforce {rng.choice(PROTOCOLS).replace('_', ' ')} training across {dept.upper()}.\n"
        f"- Update medication reconciliation workflow for {contributing_med}.\n"
        f"- Introduce structured handoff using SBAR for shift changes.\n"
    )
    return Document(
        doc_id=doc_id,
        doc_type="rca",
        title=f"RCA {doc_id}: {incident.replace('_', ' ')} in {dept.upper()}",
        content=body,
        metadata={
            "department": dept,
            "incident_type": incident,
            "root_causes": root_causes,
            "involved_medication": contributing_med,
        },
    )


def _protocol(rng: random.Random, idx: int) -> Document:
    doc_id = f"PROT-{idx:03d}"
    proto = PROTOCOLS[(idx - 1) % len(PROTOCOLS)]
    dept = _pick(rng, DEPARTMENTS)
    body = (
        f"Protocol {doc_id}: {proto.replace('_', ' ').title()}\n\n"
        f"PURPOSE\n"
        f"Defines the standard steps for {proto.replace('_', ' ')} in the {dept.upper()} and "
        f"across any unit performing equivalent workflows.\n\n"
        f"SCOPE\n"
        f"Applies to all {rng.choice(STAFF_ROLES).replace('_', ' ')} and "
        f"{rng.choice(STAFF_ROLES).replace('_', ' ')} staff, including temporary and float staff.\n\n"
        f"PROCEDURE\n"
        f"1. Verify patient identity with two identifiers.\n"
        f"2. Complete pre-procedure checklist as defined by the {proto.replace('_', ' ')} bundle.\n"
        f"3. Perform required cross-checks before administration or intervention.\n"
        f"4. Document completion in the electronic health record within 15 minutes.\n\n"
        f"REFERENCES\n"
        f"- Joint Commission National Patient Safety Goals\n"
        f"- Internal policy manual, section on {proto.replace('_', ' ')}.\n"
    )
    return Document(
        doc_id=doc_id,
        doc_type="protocol",
        title=f"Protocol {doc_id}: {proto.replace('_', ' ').title()}",
        content=body,
        metadata={"protocol": proto, "owning_department": dept},
    )


def _formulary(rng: random.Random, idx: int) -> Document:
    doc_id = f"FORM-{idx:03d}"
    med = MEDICATIONS[(idx - 1) % len(MEDICATIONS)][0]
    body = (
        f"Formulary Entry {doc_id}: {med.title()}\n\n"
        f"DRUG CLASS\n"
        f"Refer to hospital pharmacopeia for {med} classification.\n\n"
        f"INDICATIONS\n"
        f"Standard indications per current hospital formulary.\n\n"
        f"MONITORING PARAMETERS\n"
        f"- Baseline labs before initiation\n"
        f"- Trough levels as indicated\n"
        f"- Re-evaluation of dose every 24-48 hours\n\n"
        f"HIGH-ALERT STATUS\n"
        f"{med.title()} is flagged as a high-alert medication. Independent double-check is "
        f"required before administration in high-acuity settings such as the ICU and ER.\n\n"
        f"RELATED PROTOCOLS\n"
        f"- {rng.choice(PROTOCOLS).replace('_', ' ').title()}\n"
        f"- Medication Reconciliation\n"
    )
    return Document(
        doc_id=doc_id,
        doc_type="formulary",
        title=f"Formulary Entry {doc_id}: {med.title()}",
        content=body,
        metadata={"medication": med, "high_alert": True},
    )


def generate_corpus(n_aer: int = 55, n_rca: int = 25, n_prot: int = 12, n_form: int = 8) -> list[Document]:
    rng = random.Random(SEED)
    docs: list[Document] = []
    docs.extend(_aer(rng, i) for i in range(1, n_aer + 1))
    docs.extend(_rca(rng, i) for i in range(1, n_rca + 1))
    docs.extend(_protocol(rng, i) for i in range(1, n_prot + 1))
    docs.extend(_formulary(rng, i) for i in range(1, n_form + 1))
    return docs
