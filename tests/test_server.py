import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server import (
    check_fatigue_management, check_nhvas_module_compliance,
    check_chain_of_responsibility, check_pbs_vehicle_compliance,
    check_ewd_compliance, check_state_specific_rules,
    check_mass_management, prepare_nhvr_audit_pack,
    FATIGUE_LIMITS, NHVAS_MODULES, COR_PENALTIES, PBS_CLASSES,
    EWD_FACTS, STATE_RULES, MASS_LIMITS, NHVR_MAJOR_RISK_CATEGORIES,
)

def _call(t, **kw):
    fn = t.fn if hasattr(t, "fn") else t
    return fn(**kw)


# ──────────────────────────────────────────────────────────────────────
# check_fatigue_management
# ──────────────────────────────────────────────────────────────────────

def test_fatigue_standard_clean_day():
    r = _call(check_fatigue_management,
              driver_name="Driver A", fatigue_tier="standard",
              daily_log=[{"date": "2026-06-02", "work_hr": 10.0,
                          "longest_work_hr": 5.0, "shortest_break_min": 30,
                          "continuous_rest_hr": 8.0}],
              seven_day_work_hr=50.0, fourteen_day_work_hr=100.0,
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    assert r["infringement_count"] == 0
    assert r["tier"] == "standard"


def test_fatigue_standard_exceeded_24hr_work():
    r = _call(check_fatigue_management,
              driver_name="Driver B", fatigue_tier="standard",
              daily_log=[{"date": "2026-06-02", "work_hr": 13.5,
                          "longest_work_hr": 5.0, "shortest_break_min": 30,
                          "continuous_rest_hr": 8.0}],
              seven_day_work_hr=50.0, fourteen_day_work_hr=100.0,
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    codes = [i["code"] for i in r["infringements"]]
    assert "exceeded_max_work_24hr" in codes


def test_fatigue_bfm_higher_limit_passes():
    # 13.5h work passes BFM (14h limit) but failed Standard (12h limit)
    r = _call(check_fatigue_management,
              driver_name="Driver C", fatigue_tier="bfm",
              daily_log=[{"date": "2026-06-02", "work_hr": 13.5,
                          "longest_work_hr": 6.0, "shortest_break_min": 30,
                          "continuous_rest_hr": 8.0}],
              seven_day_work_hr=70.0, fourteen_day_work_hr=140.0,
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    codes = [i["code"] for i in r["infringements"]]
    assert "exceeded_max_work_24hr" not in codes


def test_fatigue_7_day_breach():
    r = _call(check_fatigue_management,
              driver_name="Driver D", fatigue_tier="standard",
              seven_day_work_hr=80.0, fourteen_day_work_hr=140.0,
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    codes = [i["code"] for i in r["infringements"]]
    assert "exceeded_7_day_work" in codes


def test_fatigue_invalid_tier_defaults_to_standard():
    r = _call(check_fatigue_management, driver_name="X", fatigue_tier="unknown",
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    assert r["tier"] == "standard"


# ──────────────────────────────────────────────────────────────────────
# check_nhvas_module_compliance
# ──────────────────────────────────────────────────────────────────────

def test_nhvas_fatigue_overdue_audit():
    r = _call(check_nhvas_module_compliance,
              operator_name="ACME Logistics", module="fatigue",
              last_compliance_audit_date="2024-01-01",
              last_internal_review_date="2024-01-01",
              accreditation_active=True)
    assert r["status"] == "ACTION_REQUIRED"
    assert any("OVERDUE" in f for f in r["findings"])


def test_nhvas_mass_within_cadence():
    from datetime import date, timedelta
    recent = (date.today() - timedelta(days=60)).isoformat()
    r = _call(check_nhvas_module_compliance,
              operator_name="ACME", module="mass",
              last_compliance_audit_date=recent,
              last_internal_review_date=recent,
              accreditation_active=True)
    assert r["status"] == "COMPLIANT"


def test_nhvas_unknown_module():
    r = _call(check_nhvas_module_compliance,
              operator_name="X", module="bogus")
    assert "error" in r


# ──────────────────────────────────────────────────────────────────────
# check_chain_of_responsibility
# ──────────────────────────────────────────────────────────────────────

def test_cor_green_band_clean_operator():
    r = _call(check_chain_of_responsibility,
              operator_name="ACME", parties=["operator", "scheduler"],
              documented_safety_system=True,
              risk_register_maintained=True,
              incidents_last_12_months=0)
    assert r["risk_band"] == "GREEN"


def test_cor_red_band_no_sms_with_incidents():
    r = _call(check_chain_of_responsibility,
              operator_name="BAD CO", parties=["operator", "loader"],
              documented_safety_system=False,
              risk_register_maintained=False,
              incidents_last_12_months=5)
    assert r["risk_band"] == "RED"
    assert "URGENT" in r["advisory"]


def test_cor_penalty_categories_present():
    r = _call(check_chain_of_responsibility,
              operator_name="X", parties=["operator"])
    assert "category_1" in r["max_penalty_reference"]
    assert r["max_penalty_reference"]["category_1"]["max_fine_corp_aud"] == 3_000_000


# ──────────────────────────────────────────────────────────────────────
# check_pbs_vehicle_compliance
# ──────────────────────────────────────────────────────────────────────

def test_pbs_not_approved_flags():
    r = _call(check_pbs_vehicle_compliance,
              vrn="ABC123", requested_pbs_level=3, approved_pbs_level=0,
              combination_type="road_train_t1", overall_length_m=35.0)
    assert r["status"] == "ACTION_REQUIRED"
    assert any("NOT PBS-approved" in f for f in r["findings"])


def test_pbs_approved_clean():
    r = _call(check_pbs_vehicle_compliance,
              vrn="XYZ789", requested_pbs_level=2, approved_pbs_level=2,
              combination_type="b_double", overall_length_m=25.0)
    assert r["status"] == "APPROVED"


def test_pbs_length_exceeds_class():
    r = _call(check_pbs_vehicle_compliance,
              vrn="LONG1", requested_pbs_level=2, approved_pbs_level=2,
              combination_type="b_double", overall_length_m=30.0)
    assert any("length" in f.lower() for f in r["findings"])


# ──────────────────────────────────────────────────────────────────────
# check_ewd_compliance
# ──────────────────────────────────────────────────────────────────────

def test_ewd_paper_diary_flagged():
    r = _call(check_ewd_compliance, driver_name="D1", using_ewd=False)
    assert r["status"] == "ACTION_REQUIRED"
    assert any("Paper diary" in f for f in r["findings"])


def test_ewd_approved_provider_clean():
    r = _call(check_ewd_compliance,
              driver_name="D2", using_ewd=True,
              ewd_provider="Teletrac Navman EWD",
              last_30_days_records_present=True)
    assert r["status"] == "COMPLIANT"


def test_ewd_unknown_provider_flagged():
    r = _call(check_ewd_compliance,
              driver_name="D3", using_ewd=True,
              ewd_provider="SomeRandomBox",
              last_30_days_records_present=True)
    assert any("not in known" in f for f in r["findings"])


# ──────────────────────────────────────────────────────────────────────
# check_state_specific_rules
# ──────────────────────────────────────────────────────────────────────

def test_state_nsw_hvnl_applies():
    r = _call(check_state_specific_rules, state="NSW", operator_name="ACME")
    assert r["hvnl_applies"] is True
    assert r["state"] == "NSW"


def test_state_wa_separate_act():
    r = _call(check_state_specific_rules, state="WA", operator_name="X")
    assert r["hvnl_applies"] is False
    assert any("HVNL does NOT directly apply" in a for a in r["advisories"])


def test_state_unknown_returns_error():
    r = _call(check_state_specific_rules, state="ZZ")
    assert "error" in r


# ──────────────────────────────────────────────────────────────────────
# check_mass_management
# ──────────────────────────────────────────────────────────────────────

def test_mass_b_double_over_gcm():
    r = _call(check_mass_management,
              vrn="BD01", combination_type="b_double", gcm_t=70.0)
    codes = [b["code"] for b in r["breaches"]]
    assert "exceeded_gcm_b_double" in codes
    assert r["status"] == "OVERLOAD_BREACH"


def test_mass_clean_b_double():
    r = _call(check_mass_management,
              vrn="BD02", combination_type="b_double", gcm_t=60.0,
              steer_axle_t=6.0, length_m=25.0, width_m=2.5, height_m=4.3)
    assert r["status"] == "COMPLIANT"
    assert r["breach_count"] == 0


def test_mass_steer_axle_overload():
    r = _call(check_mass_management,
              vrn="ST01", combination_type="rigid",
              gvm_t=10.0, steer_axle_t=7.5)
    codes = [b["code"] for b in r["breaches"]]
    assert "exceeded_steer_axle" in codes


def test_mass_tandem_axle_overload():
    r = _call(check_mass_management,
              vrn="TA01", combination_type="b_double",
              gcm_t=60.0, tandem_axle_groups_t=[17.0, 16.0])
    codes = [b["code"] for b in r["breaches"]]
    assert any(c.startswith("exceeded_tandem_group") for c in codes)


# ──────────────────────────────────────────────────────────────────────
# prepare_nhvr_audit_pack
# ──────────────────────────────────────────────────────────────────────

def test_audit_pack_has_evidence_list():
    r = _call(prepare_nhvr_audit_pack,
              operator_name="ACME", operator_id="OP-12345",
              fleet_size=30, nhvas_modules_held=["fatigue", "mass"])
    assert len(r["evidence_checklist"]) >= 10
    assert any("NHVR" in e or "NHVAS" in e for e in r["evidence_checklist"])


def test_audit_pack_lists_major_risk_categories():
    r = _call(prepare_nhvr_audit_pack, operator_name="X")
    assert len(r["major_risk_categories"]) >= 5
    assert any("Fatigue" in c for c in r["major_risk_categories"])


# ──────────────────────────────────────────────────────────────────────
# HMAC attestation
# ──────────────────────────────────────────────────────────────────────

def test_attestation_chain():
    r = _call(check_chain_of_responsibility,
              operator_name="X", parties=["operator"])
    assert "sig" in r
    assert "ts" in r
    assert r["issuer"] == "meok-nhvr-australia-mcp"
    assert r["version"] == "1.0.0"


def test_attestation_unsigned_without_key():
    # Without MEOK_HMAC_SECRET env var, signatures should be the placeholder
    r = _call(check_fatigue_management, driver_name="X",
              long_rest_hr_in_last_14d=24.0, night_rest_count_in_last_14d=2)
    # If no key configured, sig is "unsigned-no-key-configured" - else a hex digest
    assert r["sig"] in ("unsigned-no-key-configured",) or len(r["sig"]) == 64


def test_attestation_with_hmac_key_produces_hex_sig(monkeypatch):
    monkeypatch.setenv("MEOK_HMAC_SECRET", "test-secret-key")
    # Re-import to reload module-level secret
    import importlib, server as srv
    importlib.reload(srv)
    r = _call(
        srv.check_fatigue_management,
        driver_name="X", long_rest_hr_in_last_14d=24.0,
        night_rest_count_in_last_14d=2,
    )
    assert len(r["sig"]) == 64  # SHA-256 hex digest length


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
