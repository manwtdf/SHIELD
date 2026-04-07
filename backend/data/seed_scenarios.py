SCENARIO_PROFILES = {

    "scenario_1": {  # New Device + SIM
        "name": "Attacker: New Phone",
        "description": "Attacker triggers SIM swap and uses a new mobile device to access account.",
        "expected_score": 27,
        "expected_action": "BLOCK_AND_FREEZE",
        "features": {
            "inter_key_delay_mean":     (310, 60),
            "inter_key_delay_std":      (90, 20),
            "dwell_time_mean":          (140, 30),
            "swipe_velocity_mean":      (280, 80),
            "hand_stability_score":     (0.51, 0.10),
            "session_duration_ms":      (95000, 10000),
            "time_of_day_hour":         [2, 3],
            "direct_to_transfer":       1,
            "exploratory_ratio":        (0.35, 0.08),
            "time_to_submit_otp_ms":    (2100, 300),
            "is_new_device":            1,
            "device_fingerprint_delta": (0.94, 0.03),
        }
    },

    "scenario_2": {  # Laptop Browser
        "name": "Attacker: Laptop Browser",
        "description": "SIM used for OTP only, fraud executed via desktop browser (no touch telemetry).",
        "expected_score": 31,
        "expected_action": "BLOCK_TRANSACTION",
        "features": {
            "inter_key_delay_mean":     (145, 20),
            "swipe_velocity_mean":      0,
            "tap_pressure_mean":        0,
            "form_field_order_entropy": (0.85, 0.10),
            "session_duration_ms":      (110000, 15000),
            "time_of_day_hour":         [1, 2, 3],
            "direct_to_transfer":       1,
            "is_new_device":            1,
            "device_fingerprint_delta": (0.97, 0.02),
            "exploratory_ratio":        (0.28, 0.07),
            "time_to_submit_otp_ms":    (3200, 500),
        }
    },

    "scenario_3": {  # Bot Automation
        "name": "Attacker: Automated Bot",
        "description": "Scripts autofill forms at inhuman speeds with zero timing variance.",
        "expected_score": 19,
        "expected_action": "BLOCK_AND_FREEZE",
        "features": {
            "inter_key_delay_mean":     (42, 2),
            "inter_key_delay_std":      (1.5, 0.3),
            "click_speed_std":          (0.8, 0.2),
            "time_to_submit_otp_ms":    (800, 50),
            "interaction_pace_ratio":   (0.05, 0.01),
            "typing_burst_count":       1,
            "error_rate":               0,
            "direct_to_transfer":       1,
            "session_duration_ms":      (45000, 3000),
            "exploratory_ratio":        (0.01, 0.005),
            "is_new_device":            1,
        }
    },

    "scenario_4": {  # Direct-to-transfer
        "name": "Attacker: Direct-to-Transfer",
        "description": "Attacker skips all browsing and goes directly to large fund transfer.",
        "expected_score": 42,
        "expected_action": "BLOCK_TRANSACTION",
        "features": {
            "inter_key_delay_mean":     (190, 25),
            "session_duration_ms":      (30000, 5000),
            "direct_to_transfer":       1,
            "screens_visited_count":    2,
            "exploratory_ratio":        0,
            "time_to_submit_otp_ms":    (4500, 800),
            "is_new_device":            1,
        }
    },

    "scenario_5": {  # Same Device Takeover
        "name": "Attacker: Same-Device Takeover",
        "description": "Attacker has physical device. Behavior differs slightly from owner.",
        "expected_score": 48,
        "expected_action": "STEP_UP_AUTH",
        "features": {
            "inter_key_delay_mean":     (210, 35),
            "session_duration_ms":      (95000, 8000),
            "direct_to_transfer":       1,
            "time_of_day_hour":         [3, 4],
            "time_to_submit_otp_ms":    (3800, 600),
            "exploratory_ratio":        (0.18, 0.05),
            "is_new_device":            0,
            "device_fingerprint_delta": (0.08, 0.02),
            "hand_stability_score":     (0.71, 0.08),
        }
    },

    "legitimate": { # Control Group
        "name": "Legitimate User",
        "description": "Consistent, habitual behavior for validation.",
        "expected_score": 91,
        "expected_action": "ALLOW",
        "features": {
            "inter_key_delay_mean":     (180, 15),
            "inter_key_delay_std":      (25, 5),
            "inter_key_delay_p95":      (280, 20),
            "dwell_time_mean":          (95, 8),
            "dwell_time_std":           (12, 3),
            "error_rate":               (0.04, 0.01),
            "backspace_frequency":      (2.1, 0.5),
            "typing_burst_count":       (4, 1),
            "words_per_minute":         (38, 4),
            "swipe_velocity_mean":      (450, 30),
            "hand_stability_score":     (0.82, 0.05),
            "session_duration_ms":      (240000, 30000),
            "time_of_day_hour":         [9, 10, 18, 19, 20],
            "direct_to_transfer":       0.15,
            "exploratory_ratio":        (0.08, 0.02),
            "time_to_submit_otp_ms":    (8500, 2000),
            "is_new_device":            0,
            "device_fingerprint_delta": (0.05, 0.01),
            "timezone_changed":         0,
            "os_version_changed":       0,
        }
    },
    "scenario_6": {  # Pre-Auth SIM Probe
        "name": "Attacker: Pre-Auth SIM Probe",
        "description": "Detection fires before login via telecom/SMS pattern (3 calls in 2 minutes).",
        "expected_score": 0,
        "expected_action": "BLOCK_TRANSACTION",
        "features": {
             # Pre-auth has no behavioral vector, but we fill with 0s for schema safety
        }
    }
}
