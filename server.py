#!/usr/bin/env python3
"""
MEOK NHVR Australia Compliance MCP
====================================

By MEOK AI Labs - https://haulage.app - MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-nhvr-australia-mcp -->

WHAT THIS DOES
--------------
Australia has ~200,000 heavy vehicles under NHVR oversight. Operators face:

  - Chain of Responsibility (CoR) penalties: up to AUD 3m + 5yr prison
  - NHVR roadside interventions + Major Risk Category enforcement
  - NHVAS accreditation required to access Mass/Fatigue/Maintenance concessions
  - Electronic Work Diary (EWD) replacing paper diaries from May 2023
  - Performance-Based Standards (PBS) for road-trains + truck-and-dog combos

This MCP gives Compliance Managers + fleet operators the callable toolkit to
PREVENT NHVR enforcement action and maintain NHVAS accreditation.

TOOLS (8)
---------
- check_fatigue_management(driver_log)            -> HVNL Standard/BFM/AFM rest rules
- check_nhvas_module_compliance(operator, module) -> Mass/Maintenance/Fatigue audit cadence
- check_chain_of_responsibility(operator_data)    -> CoR primary duty obligations
- check_pbs_vehicle_compliance(vehicle_spec)      -> PBS road-train / truck-and-dog approval
- check_ewd_compliance(driver_data)               -> EWD vs paper diary (May 2023 mandate)
- check_state_specific_rules(state, operator)     -> NSW/VIC/QLD/SA/WA/TAS variations
- check_mass_management(vehicle_loads)            -> GVM/GCM/axle/dimension limits
- prepare_nhvr_audit_pack(operator_data)          -> NHVR roadside intervention prep

WHY YOU PAY
-----------
One avoided CoR prosecution = AUD 50k-3m saved (fines + legal + reputational).
One avoided NHVAS loss = AUD 200k+/yr in lost mass/maintenance concessions.
AUD 49/mo Starter is a rounding error vs the exposure.

PRICING
-------
Free MIT self-host  -  AUD 49/mo Starter  -  AUD 149/mo Pro  -  AUD 999/mo Fleet.

REGULATORY BASIS
----------------
Heavy Vehicle National Law (HVNL) - NSW, VIC, QLD, SA, TAS, ACT (WA/NT mirror)
NHVR Heavy Vehicle Accreditation Scheme (NHVAS) - Mass/Maintenance/Fatigue modules
Chain of Responsibility (CoR) primary duties (HVNL Part 1A)
Performance-Based Standards (PBS) scheme
Electronic Work Diary (EWD) - May 2023+ (transitional paper allowed)
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, date, timedelta
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-nhvr-australia")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# Regulatory tables - HVNL Fatigue Management
# ──────────────────────────────────────────────────────────────────────

# Standard Hours (no accreditation required) - HVNL Schedule 1 Part 1
FATIGUE_STANDARD_HOURS = {
    "max_work_per_24hr": 12.0,            # 12h work in any 24h
    "min_rest_per_24hr": 7.0,             # 7h continuous rest (with stationary rest)
    "max_continuous_work_hr": 5.25,       # 5h15 before break required
    "min_short_rest_min": 15,             # 15 min continuous rest
    "max_work_per_7_days": 72.0,          # 72h max in 7 days
    "max_work_per_14_days": 144.0,        # 144h max in 14 days
    "min_long_rest_per_14d_hr": 24.0,     # at least 24h continuous in 14 days
    "min_night_rest_count_14d": 2,        # 2 nights of 7h continuous between 10pm-8am
}

# Basic Fatigue Management (BFM) - allows longer work periods with accreditation
FATIGUE_BFM = {
    "max_work_per_24hr": 14.0,            # 14h work in any 24h
    "min_rest_per_24hr": 7.0,
    "max_continuous_work_hr": 6.25,       # 6h15 before break
    "min_short_rest_min": 15,
    "max_work_per_7_days": 84.0,          # 84h max in 7 days
    "max_work_per_14_days": 154.0,        # 154h max in 14 days
    "min_long_rest_per_14d_hr": 24.0,
    "min_night_rest_count_14d": 2,
}

# Advanced Fatigue Management (AFM) - operator-specific outer limits via NHVR approval
FATIGUE_AFM = {
    "max_work_per_24hr": 15.5,            # 15h30 approved outer limit
    "min_rest_per_24hr": 6.0,
    "max_continuous_work_hr": 7.0,
    "max_work_per_7_days": 96.0,
    "max_work_per_14_days": 168.0,
    "note": "AFM is operator-specific; values shown are typical NHVR-approved outer limits.",
}

FATIGUE_LIMITS = {
    "standard": FATIGUE_STANDARD_HOURS,
    "bfm": FATIGUE_BFM,
    "afm": FATIGUE_AFM,
}

# NHVAS modules - audit cadence + scope
NHVAS_MODULES = {
    "mass": {
        "purpose": "Higher mass concessions (HML/CML)",
        "entry_audit": "Within 90 days of accreditation",
        "compliance_audit_months": 24,    # 2-yearly
        "internal_review_months": 12,
        "key_evidence": ["weighbridge records", "axle mass records",
                         "load distribution", "loading docs"],
    },
    "maintenance": {
        "purpose": "Self-managed roadworthiness; PBS access",
        "entry_audit": "Within 90 days of accreditation",
        "compliance_audit_months": 24,
        "internal_review_months": 12,
        "key_evidence": ["maintenance schedules", "daily checks",
                         "fault reports", "repair records", "qualifications"],
    },
    "fatigue": {
        "purpose": "BFM or AFM hours of work concessions",
        "entry_audit": "Within 90 days of accreditation",
        "compliance_audit_months": 12,    # Fatigue is annual
        "internal_review_months": 6,
        "key_evidence": ["driver schedules", "work diary records",
                         "fitness for duty", "training records",
                         "rostering systems"],
    },
}

# Chain of Responsibility primary duties (HVNL Part 1A, s26C)
COR_PARTY_DUTIES = {
    "employer": "Employer of driver - ensure safety of transport activities",
    "prime_contractor": "Engager of driver - same primary duty",
    "operator": "Operator of vehicle - vehicle safety + driver compliance",
    "scheduler": "Schedules vehicle/driver - reasonable schedules",
    "consignor": "Sends goods - safe loading + accurate description",
    "consignee": "Receives goods - reasonable timeslots + unloading",
    "loader": "Loads vehicle - mass + dimension + restraint compliance",
    "loading_manager": "Manages loading premises - safe loading systems",
    "packer": "Packs goods - accurate description + safe packing",
}

# CoR penalty bands (HVNL s26F/s26G)
COR_PENALTIES = {
    "category_1": {
        "label": "Reckless conduct - serious risk of death/injury",
        "max_fine_corp_aud": 3_000_000,
        "max_fine_individual_aud": 300_000,
        "max_prison_yrs": 5,
    },
    "category_2": {
        "label": "Failure to comply - risk of death/injury",
        "max_fine_corp_aud": 1_500_000,
        "max_fine_individual_aud": 150_000,
        "max_prison_yrs": 0,
    },
    "category_3": {
        "label": "Failure to comply - duty breach (no specific risk)",
        "max_fine_corp_aud": 500_000,
        "max_fine_individual_aud": 50_000,
        "max_prison_yrs": 0,
    },
}

# Performance-Based Standards (PBS) vehicle classes
PBS_CLASSES = {
    "level_1": {"label": "Urban/general access", "max_length_m": 20.0,
                "typical": "Truck-and-dog, B-double light"},
    "level_2": {"label": "B-double approved", "max_length_m": 26.0,
                "typical": "B-double, heavy truck-and-dog"},
    "level_3": {"label": "Type 1 road-train", "max_length_m": 36.5,
                "typical": "Type 1 road-train, B-triple"},
    "level_4": {"label": "Type 2 road-train", "max_length_m": 53.5,
                "typical": "Type 2 road-train, A-triple"},
}

# Electronic Work Diary (EWD) approved providers + key dates
EWD_FACTS = {
    "mandate_date": "2023-05-01",
    "paper_still_allowed": True,
    "note": "EWD is voluntary - paper diary remains valid. EWDs must be NHVR-approved.",
    "approved_provider_examples": ["Teletrac Navman EWD", "EROAD EWD",
                                    "Transtech EWD", "MTData EWD", "Coretex EWD"],
    "key_benefit": "Auto-records work/rest; reduces driver admin + infringement risk.",
}

# Mass management - National HVNL standard limits
MASS_LIMITS = {
    "gvm_general_access_t": 42.5,        # general-access tandem-axle truck-and-dog
    "gcm_b_double_t": 62.5,              # B-double general access
    "gcm_type_1_road_train_t": 79.0,     # Type 1 road-train (3 trailers)
    "gcm_type_2_road_train_t": 115.5,    # Type 2 road-train
    "max_steer_axle_t": 6.5,
    "max_single_axle_t": 9.0,
    "max_tandem_axle_group_t": 16.5,
    "max_tri_axle_group_t": 20.0,
    "max_length_general_m": 19.0,
    "max_length_b_double_m": 26.0,
    "max_width_m": 2.5,                  # 2.5m general; 2.55m refrigerated
    "max_height_m": 4.3,
}

# State-specific variations (key deltas from National HVNL)
STATE_RULES = {
    "NSW": {
        "hvnl_applies": True,
        "notes": "Full HVNL state. CoR enforced by TfNSW + NHVR.",
        "key_variation": "Sydney curfew zones for road-trains; M5/M7 toll concessions.",
    },
    "VIC": {
        "hvnl_applies": True,
        "notes": "Full HVNL state. CoR enforced by VicRoads + NHVR.",
        "key_variation": "VIC PBS network differs slightly - check HVRG approval.",
    },
    "QLD": {
        "hvnl_applies": True,
        "notes": "Full HVNL state. CoR enforced by TMR + NHVR.",
        "key_variation": "QLD has multi-combination route approvals; cane sugar season uplifts.",
    },
    "SA": {
        "hvnl_applies": True,
        "notes": "Full HVNL state.",
        "key_variation": "SA grain harvest seasonal mass uplift.",
    },
    "TAS": {
        "hvnl_applies": True,
        "notes": "Full HVNL state. Smaller fleet base.",
        "key_variation": "TAS bridge constraints limit road-train access.",
    },
    "ACT": {
        "hvnl_applies": True,
        "notes": "Full HVNL.",
        "key_variation": "Limited road-train access in ACT.",
    },
    "WA": {
        "hvnl_applies": False,
        "notes": "WA has its own Heavy Vehicle Act (mirrors most HVNL).",
        "key_variation": "Main Roads WA permits; RAV Network instead of NHVR PBS.",
    },
    "NT": {
        "hvnl_applies": False,
        "notes": "NT has its own Heavy Vehicle Act (mirrors most HVNL).",
        "key_variation": "NT permits via Department of Infrastructure, Planning and Logistics.",
    },
}

# NHVR Major Risk Categories - roadside intervention triggers
NHVR_MAJOR_RISK_CATEGORIES = [
    "Fatigue management (work/rest non-compliance)",
    "Mass, dimension + loading (overloading/oversize)",
    "Speed compliance",
    "Vehicle standards (roadworthiness defects)",
    "Driver licensing + qualification",
    "Dangerous goods carriage",
    "Chain of Responsibility breaches",
]


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(
        _HMAC_SECRET.encode(),
        json.dumps(payload, sort_keys=True, default=str).encode(),
        hashlib.sha256,
    ).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attestation(payload: dict) -> dict:
    return {**payload, "ts": _ts(), "sig": _sign(payload),
            "issuer": "meok-nhvr-australia-mcp", "version": "1.0.0"}


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def check_fatigue_management(
    driver_name: str = "",
    fatigue_tier: str = "standard",
    daily_log: Optional[list] = None,
    seven_day_work_hr: float = 0.0,
    fourteen_day_work_hr: float = 0.0,
    long_rest_hr_in_last_14d: float = 0.0,
    night_rest_count_in_last_14d: int = 0,
) -> dict:
    """Check HVNL fatigue rules against Standard / BFM / AFM tier.

    Args:
      fatigue_tier: 'standard' / 'bfm' / 'afm'
      daily_log: list of dicts like
        {"date": "2026-06-02", "work_hr": 12.5, "longest_work_hr": 5.5,
         "shortest_break_min": 15, "continuous_rest_hr": 7.0}
      seven_day_work_hr: total work hours in the trailing 7 days
      fourteen_day_work_hr: total work hours in the trailing 14 days
      long_rest_hr_in_last_14d: longest continuous rest period in last 14 days
      night_rest_count_in_last_14d: number of 7h+ night rests (10pm-8am) in last 14d
    """
    daily_log = daily_log or []
    tier = fatigue_tier.lower().strip()
    if tier not in FATIGUE_LIMITS:
        tier = "standard"
    limits = FATIGUE_LIMITS[tier]
    infringements = []

    for d in daily_log:
        wd = d.get("work_hr", 0)
        if wd > limits.get("max_work_per_24hr", 12.0):
            infringements.append({
                "code": "exceeded_max_work_24hr",
                "date": d.get("date"),
                "actual_hr": wd,
                "limit_hr": limits["max_work_per_24hr"],
                "tier": tier,
            })
        lw = d.get("longest_work_hr", 0)
        if lw > limits.get("max_continuous_work_hr", 5.25):
            infringements.append({
                "code": "exceeded_continuous_work",
                "date": d.get("date"),
                "actual_hr": lw,
                "limit_hr": limits["max_continuous_work_hr"],
                "tier": tier,
            })
        sb = d.get("shortest_break_min", 15)
        if sb < limits.get("min_short_rest_min", 15):
            infringements.append({
                "code": "insufficient_short_rest",
                "date": d.get("date"),
                "actual_min": sb,
                "limit_min": limits["min_short_rest_min"],
                "tier": tier,
            })
        cr = d.get("continuous_rest_hr", 24)
        if cr < limits.get("min_rest_per_24hr", 7.0):
            infringements.append({
                "code": "insufficient_24hr_rest",
                "date": d.get("date"),
                "actual_hr": cr,
                "limit_hr": limits["min_rest_per_24hr"],
                "tier": tier,
            })

    if seven_day_work_hr > limits.get("max_work_per_7_days", 72.0):
        infringements.append({
            "code": "exceeded_7_day_work",
            "actual_hr": seven_day_work_hr,
            "limit_hr": limits["max_work_per_7_days"],
            "tier": tier,
        })
    if fourteen_day_work_hr > limits.get("max_work_per_14_days", 144.0):
        infringements.append({
            "code": "exceeded_14_day_work",
            "actual_hr": fourteen_day_work_hr,
            "limit_hr": limits["max_work_per_14_days"],
            "tier": tier,
        })
    if long_rest_hr_in_last_14d < limits.get("min_long_rest_per_14d_hr", 24.0):
        infringements.append({
            "code": "insufficient_long_rest_14d",
            "actual_hr": long_rest_hr_in_last_14d,
            "limit_hr": limits["min_long_rest_per_14d_hr"],
            "tier": tier,
        })
    if night_rest_count_in_last_14d < limits.get("min_night_rest_count_14d", 2):
        infringements.append({
            "code": "insufficient_night_rest_count",
            "actual_count": night_rest_count_in_last_14d,
            "limit_count": limits["min_night_rest_count_14d"],
            "tier": tier,
        })

    payload = {
        "tool": "check_fatigue_management",
        "driver_name": driver_name,
        "tier": tier,
        "limits_applied": limits,
        "infringement_count": len(infringements),
        "infringements": infringements,
        "advisory": (
            "Clean - meets HVNL fatigue rules for tier."
            if not infringements else
            f"{len(infringements)} fatigue infringement(s) - actioned letter + retraining required; risk of HVNL prosecution."
        ),
    }
    return _attestation(payload)


@mcp.tool()
def check_nhvas_module_compliance(
    operator_name: str = "",
    module: str = "fatigue",
    last_entry_audit_date: str = "",
    last_compliance_audit_date: str = "",
    last_internal_review_date: str = "",
    accreditation_active: bool = True,
) -> dict:
    """Check NHVAS module audit cadence: Mass / Maintenance / Fatigue.

    Args:
      module: 'mass' / 'maintenance' / 'fatigue'
      last_compliance_audit_date: ISO date of last NHVAS compliance audit
      last_internal_review_date: ISO date of last internal review
    """
    mod = module.lower().strip()
    if mod not in NHVAS_MODULES:
        return _attestation({
            "tool": "check_nhvas_module_compliance",
            "error": f"Unknown module '{module}' - use mass / maintenance / fatigue",
            "valid_modules": list(NHVAS_MODULES.keys()),
        })
    spec = NHVAS_MODULES[mod]
    today = date.today()

    def _months_since(iso: str) -> Optional[float]:
        try:
            d = date.fromisoformat(iso)
            days = (today - d).days
            return round(days / 30.44, 1)
        except Exception:
            return None

    months_since_compliance = _months_since(last_compliance_audit_date)
    months_since_review = _months_since(last_internal_review_date)

    findings = []
    if not accreditation_active:
        findings.append("Accreditation INACTIVE - module concessions not available.")
    if months_since_compliance is None:
        findings.append("No compliance audit on record.")
    elif months_since_compliance > spec["compliance_audit_months"]:
        findings.append(
            f"Compliance audit OVERDUE - {months_since_compliance} months since last (limit {spec['compliance_audit_months']})."
        )
    if months_since_review is None:
        findings.append("No internal review on record.")
    elif months_since_review > spec["internal_review_months"]:
        findings.append(
            f"Internal review OVERDUE - {months_since_review} months since last (limit {spec['internal_review_months']})."
        )

    return _attestation({
        "tool": "check_nhvas_module_compliance",
        "operator_name": operator_name,
        "module": mod,
        "module_spec": spec,
        "last_entry_audit_date": last_entry_audit_date,
        "last_compliance_audit_date": last_compliance_audit_date,
        "last_internal_review_date": last_internal_review_date,
        "months_since_compliance_audit": months_since_compliance,
        "months_since_internal_review": months_since_review,
        "accreditation_active": accreditation_active,
        "findings": findings,
        "status": "COMPLIANT" if not findings else "ACTION_REQUIRED",
        "next_step": (
            "OK - schedule next internal review per cadence."
            if not findings else
            "Book NHVAS auditor + run gap-close on key evidence list within 30 days."
        ),
    })


@mcp.tool()
def check_chain_of_responsibility(
    operator_name: str = "",
    parties: Optional[list] = None,
    documented_safety_system: bool = False,
    risk_register_maintained: bool = False,
    incidents_last_12_months: int = 0,
) -> dict:
    """Assess Chain of Responsibility exposure under HVNL Part 1A.

    Args:
      parties: list of CoR party roles in the chain
        e.g. ["operator", "consignor", "loader", "scheduler"]
      documented_safety_system: SMS exists + signed-off
      risk_register_maintained: live risk register updated within 90d
    """
    parties = parties or []
    party_duties = []
    for p in parties:
        key = p.lower().strip()
        if key in COR_PARTY_DUTIES:
            party_duties.append({"role": key, "primary_duty": COR_PARTY_DUTIES[key]})
        else:
            party_duties.append({"role": key, "primary_duty": "Unknown role - check HVNL Part 1A."})

    risk_score = 0
    risk_factors = []
    if not documented_safety_system:
        risk_score += 4
        risk_factors.append("No documented safety management system")
    if not risk_register_maintained:
        risk_score += 3
        risk_factors.append("Risk register stale or missing")
    if incidents_last_12_months >= 1:
        risk_score += 2 * min(incidents_last_12_months, 5)
        risk_factors.append(f"{incidents_last_12_months} incident(s) in last 12 months")

    if risk_score == 0:
        category_risk = "category_3_low"
        band = "GREEN"
    elif risk_score < 5:
        category_risk = "category_3_likely"
        band = "AMBER"
    elif risk_score < 10:
        category_risk = "category_2_likely"
        band = "AMBER"
    else:
        category_risk = "category_1_possible"
        band = "RED"

    return _attestation({
        "tool": "check_chain_of_responsibility",
        "operator_name": operator_name,
        "parties_in_chain": party_duties,
        "documented_safety_system": documented_safety_system,
        "risk_register_maintained": risk_register_maintained,
        "incidents_last_12_months": incidents_last_12_months,
        "risk_score": risk_score,
        "risk_band": band,
        "exposure_category": category_risk,
        "risk_factors": risk_factors,
        "max_penalty_reference": COR_PENALTIES,
        "advisory": (
            "Low CoR risk - maintain documentation cadence."
            if band == "GREEN" else
            "Stand up SMS + risk register; brief named officers; schedule CoR training."
            if band == "AMBER" else
            "URGENT - engage HVNL solicitor; document gap-close plan; brief executive officers on personal liability."
        ),
    })


@mcp.tool()
def check_pbs_vehicle_compliance(
    vrn: str = "",
    requested_pbs_level: int = 2,
    approved_pbs_level: int = 0,
    proposed_routes: Optional[list] = None,
    combination_type: str = "b_double",
    overall_length_m: float = 0.0,
    overall_mass_t: float = 0.0,
) -> dict:
    """Performance-Based Standards (PBS) eligibility check.

    Args:
      requested_pbs_level: 1/2/3/4
      approved_pbs_level: 0 if not yet approved
      combination_type: 'truck_and_dog' / 'b_double' / 'b_triple' / 'road_train_t1' / 'road_train_t2'
    """
    proposed_routes = proposed_routes or []
    key_req = f"level_{requested_pbs_level}"
    key_apr = f"level_{approved_pbs_level}" if approved_pbs_level >= 1 else None

    requested_spec = PBS_CLASSES.get(key_req, {})
    approved_spec = PBS_CLASSES.get(key_apr or "", {}) if key_apr else {}

    findings = []
    if approved_pbs_level == 0:
        findings.append("Vehicle NOT PBS-approved - requires PBS Design + In-Service approval before road use.")
    elif approved_pbs_level < requested_pbs_level:
        findings.append(
            f"Approval level {approved_pbs_level} < requested {requested_pbs_level} - escalate via PBS Review Panel."
        )
    if overall_length_m and requested_spec.get("max_length_m"):
        if overall_length_m > requested_spec["max_length_m"]:
            findings.append(
                f"Overall length {overall_length_m}m exceeds Level {requested_pbs_level} max {requested_spec['max_length_m']}m."
            )

    return _attestation({
        "tool": "check_pbs_vehicle_compliance",
        "vrn": vrn,
        "combination_type": combination_type,
        "requested_pbs_level": requested_pbs_level,
        "approved_pbs_level": approved_pbs_level,
        "requested_class_spec": requested_spec,
        "approved_class_spec": approved_spec,
        "overall_length_m": overall_length_m,
        "overall_mass_t": overall_mass_t,
        "proposed_routes": proposed_routes,
        "findings": findings,
        "status": "APPROVED" if not findings else "ACTION_REQUIRED",
        "next_step": (
            "OK - check route gazettal + bridge classifications for proposed routes."
            if not findings else
            "Engage PBS assessor; complete safety + infrastructure standards before commencing operations."
        ),
        "pbs_levels_reference": PBS_CLASSES,
    })


@mcp.tool()
def check_ewd_compliance(
    driver_name: str = "",
    using_ewd: bool = False,
    ewd_provider: str = "",
    paper_diary_as_backup: bool = True,
    last_30_days_records_present: bool = True,
) -> dict:
    """Electronic Work Diary compliance check (May 2023+).

    EWD is voluntary - paper still allowed - but adoption reduces infringement risk.
    EWD providers must be NHVR-approved.
    """
    findings = []
    if using_ewd:
        if not ewd_provider:
            findings.append("EWD declared but no provider named - confirm NHVR approval status.")
        elif ewd_provider not in EWD_FACTS["approved_provider_examples"]:
            findings.append(
                f"Provider '{ewd_provider}' not in known NHVR-approved list - verify directly with NHVR."
            )
    else:
        findings.append("Paper diary in use - higher infringement + transcription error risk.")

    if not last_30_days_records_present:
        findings.append("Missing records in last 30 days - reconstruct from EWD/paper + GPS evidence.")

    return _attestation({
        "tool": "check_ewd_compliance",
        "driver_name": driver_name,
        "using_ewd": using_ewd,
        "ewd_provider": ewd_provider,
        "paper_diary_as_backup": paper_diary_as_backup,
        "last_30_days_records_present": last_30_days_records_present,
        "ewd_facts": EWD_FACTS,
        "findings": findings,
        "status": "COMPLIANT" if not findings else "ACTION_REQUIRED",
        "advisory": (
            "OK - EWD with approved provider + records intact."
            if not findings else
            "Migrate to EWD for audit defensibility; verify provider NHVR approval; reconcile missing records."
        ),
    })


@mcp.tool()
def check_state_specific_rules(
    state: str = "",
    operator_name: str = "",
    operates_road_trains: bool = False,
    operates_b_doubles: bool = True,
) -> dict:
    """State-specific HVNL variations for NSW / VIC / QLD / SA / TAS / ACT / WA / NT."""
    code = state.upper().strip()
    spec = STATE_RULES.get(code)
    if not spec:
        return _attestation({
            "tool": "check_state_specific_rules",
            "error": f"Unknown state '{state}' - use NSW/VIC/QLD/SA/TAS/ACT/WA/NT",
            "valid_states": list(STATE_RULES.keys()),
        })

    advisories = [spec["key_variation"]]
    if not spec["hvnl_applies"]:
        advisories.append(
            f"{code} operates its own Heavy Vehicle Act (HVNL does NOT directly apply) - dual-jurisdiction operators must run both compliance regimes."
        )
    if operates_road_trains and code in ("TAS", "ACT"):
        advisories.append(f"{code} has limited road-train routes - check gazetted routes before scheduling.")
    if operates_b_doubles and code == "VIC":
        advisories.append("VIC PBS B-double network has VICRoads-specific overlays - confirm before route planning.")

    return _attestation({
        "tool": "check_state_specific_rules",
        "operator_name": operator_name,
        "state": code,
        "hvnl_applies": spec["hvnl_applies"],
        "notes": spec["notes"],
        "key_variation": spec["key_variation"],
        "advisories": advisories,
    })


@mcp.tool()
def check_mass_management(
    vrn: str = "",
    combination_type: str = "b_double",
    gvm_t: float = 0.0,
    gcm_t: float = 0.0,
    steer_axle_t: float = 0.0,
    single_axle_groups_t: Optional[list] = None,
    tandem_axle_groups_t: Optional[list] = None,
    tri_axle_groups_t: Optional[list] = None,
    length_m: float = 0.0,
    width_m: float = 0.0,
    height_m: float = 0.0,
    has_mass_module: bool = False,
) -> dict:
    """Mass + dimension compliance against HVNL National limits.

    Args:
      combination_type: 'rigid' / 'truck_and_dog' / 'b_double' / 'road_train_t1' / 'road_train_t2'
      has_mass_module: NHVAS Mass module accredited (unlocks HML/CML concessions)
    """
    single_axle_groups_t = single_axle_groups_t or []
    tandem_axle_groups_t = tandem_axle_groups_t or []
    tri_axle_groups_t = tri_axle_groups_t or []
    breaches = []

    if combination_type == "b_double" and gcm_t > MASS_LIMITS["gcm_b_double_t"]:
        breaches.append({
            "code": "exceeded_gcm_b_double",
            "actual_t": gcm_t,
            "limit_t": MASS_LIMITS["gcm_b_double_t"],
        })
    elif combination_type == "road_train_t1" and gcm_t > MASS_LIMITS["gcm_type_1_road_train_t"]:
        breaches.append({
            "code": "exceeded_gcm_road_train_t1",
            "actual_t": gcm_t,
            "limit_t": MASS_LIMITS["gcm_type_1_road_train_t"],
        })
    elif combination_type == "road_train_t2" and gcm_t > MASS_LIMITS["gcm_type_2_road_train_t"]:
        breaches.append({
            "code": "exceeded_gcm_road_train_t2",
            "actual_t": gcm_t,
            "limit_t": MASS_LIMITS["gcm_type_2_road_train_t"],
        })
    elif combination_type in ("rigid", "truck_and_dog") and gvm_t > MASS_LIMITS["gvm_general_access_t"]:
        breaches.append({
            "code": "exceeded_gvm_general_access",
            "actual_t": gvm_t,
            "limit_t": MASS_LIMITS["gvm_general_access_t"],
        })

    if steer_axle_t > MASS_LIMITS["max_steer_axle_t"]:
        breaches.append({
            "code": "exceeded_steer_axle",
            "actual_t": steer_axle_t,
            "limit_t": MASS_LIMITS["max_steer_axle_t"],
        })
    for idx, ax in enumerate(single_axle_groups_t):
        if ax > MASS_LIMITS["max_single_axle_t"]:
            breaches.append({"code": f"exceeded_single_axle_{idx}",
                             "actual_t": ax, "limit_t": MASS_LIMITS["max_single_axle_t"]})
    for idx, ax in enumerate(tandem_axle_groups_t):
        if ax > MASS_LIMITS["max_tandem_axle_group_t"]:
            breaches.append({"code": f"exceeded_tandem_group_{idx}",
                             "actual_t": ax, "limit_t": MASS_LIMITS["max_tandem_axle_group_t"]})
    for idx, ax in enumerate(tri_axle_groups_t):
        if ax > MASS_LIMITS["max_tri_axle_group_t"]:
            breaches.append({"code": f"exceeded_tri_group_{idx}",
                             "actual_t": ax, "limit_t": MASS_LIMITS["max_tri_axle_group_t"]})

    if width_m and width_m > MASS_LIMITS["max_width_m"]:
        breaches.append({"code": "exceeded_width", "actual_m": width_m,
                         "limit_m": MASS_LIMITS["max_width_m"]})
    if height_m and height_m > MASS_LIMITS["max_height_m"]:
        breaches.append({"code": "exceeded_height", "actual_m": height_m,
                         "limit_m": MASS_LIMITS["max_height_m"]})

    return _attestation({
        "tool": "check_mass_management",
        "vrn": vrn,
        "combination_type": combination_type,
        "has_mass_module": has_mass_module,
        "limits_reference": MASS_LIMITS,
        "breach_count": len(breaches),
        "breaches": breaches,
        "status": "COMPLIANT" if not breaches else "OVERLOAD_BREACH",
        "advisory": (
            "OK - all mass + dimension limits met."
            if not breaches else
            "OFFLOAD or REDISTRIBUTE before departure - mass breaches trigger CoR loader/consignor/operator liability; NHVR penalties apply."
        ),
        "concession_note": (
            "Mass module accredited - HML/CML concessions available on gazetted routes."
            if has_mass_module else
            "No Mass module - operating at General Mass Limits (GML) only."
        ),
    })


@mcp.tool()
def prepare_nhvr_audit_pack(
    operator_name: str = "",
    operator_id: str = "",
    fleet_size: int = 0,
    nhvas_modules_held: Optional[list] = None,
    upcoming_intervention_date: str = "",
) -> dict:
    """Prepare evidence pack for NHVR roadside intervention or scheduled audit.

    Covers the seven NHVR Major Risk Categories + NHVAS audit evidence.
    """
    nhvas_modules_held = nhvas_modules_held or []
    return _attestation({
        "tool": "prepare_nhvr_audit_pack",
        "operator_name": operator_name,
        "operator_id": operator_id,
        "fleet_size": fleet_size,
        "nhvas_modules_held": nhvas_modules_held,
        "upcoming_intervention_date": upcoming_intervention_date,
        "major_risk_categories": NHVR_MAJOR_RISK_CATEGORIES,
        "evidence_checklist": [
            "NHVR operator accreditation certificate (NHVAS modules held)",
            "Vehicle list cross-referenced to registration database",
            "Last 12 months work diary records (EWD download or paper)",
            "Driver licence + CoR training records",
            "Driver fatigue management policy + roster evidence",
            "Vehicle maintenance schedules + daily check sheets",
            "Major defect reports + repair records (12 months)",
            "Weighbridge tickets + axle-mass records (Mass module)",
            "Load restraint guide compliance evidence",
            "Risk register + Safety Management System documents",
            "Chain of Responsibility - executive officer briefings",
            "Incident register + investigation reports (12 months)",
            "PBS Design + In-Service approval certificates (if PBS)",
            "Dangerous Goods accreditation (if applicable)",
            "Insurance certificates",
        ],
        "common_findings_to_pre_check": [
            "Stale internal review (>12 months for Fatigue, >12 months for Mass/Maintenance)",
            "Missing fatigue training records",
            "Incomplete daily defect-check sheets",
            "No risk register or risk register >90 days stale",
            "Weighbridge records gap > 30 days",
            "Executive officers not briefed on CoR personal liability",
            "PBS vehicle operating outside approved route",
        ],
        "advisory": (
            "Pack ready - run dry-run audit with internal auditor 7 days before intervention."
        ),
    })


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


# ── MEOK monetization layer (Stripe upgrade · PAYG · pricing) ──────────
# Free tier is zero-config. Upgrade to Pro (unlimited) or pay-as-you-go per call.
import os as _meok_os
MEOK_STRIPE_UPGRADE = "https://buy.stripe.com/00wfZjcgAeUW4c5cyQ8k90K"  # Pro (unlimited)
MEOK_PAYG_KEY = _meok_os.environ.get("MEOK_PAYG_KEY", "")  # set to enable PAYG (x402 / ~GBP0.05 per call)
MEOK_PRICING = "https://meok.ai/pricing"


def meok_upsell(tier: str = "free") -> dict:
    """Monetization options for free-tier callers: Pro upgrade, PAYG, or pricing page."""
    if tier != "free":
        return {}
    return {"upgrade_url": MEOK_STRIPE_UPGRADE,
            "payg_enabled": bool(MEOK_PAYG_KEY),
            "pricing": MEOK_PRICING}
