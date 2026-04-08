"""
data/profiles.json — 55-feature behavioral distribution params

Structure per scenario:
  - list[mean, std] → sample from Normal(mean, std), clamp to >= 0
  - scalar           → fixed value (no noise)
  - list[...choices] → sample uniformly from the list (for categorical/hour fields)

Missing features in attacker profiles fall back to legitimate baseline,
then attacker overrides are applied on top.

All continuous features get ±8% within-person variance applied by seed_legitimate.py.
Attacker features deliberately exceed 2.5 sigma on at least 4 dimensions.
"""

PROFILES = {

  "legitimate": {
    # Touch Dynamics
    "tap_pressure_mean":           [0.55, 0.06],
    "tap_pressure_std":            [0.08, 0.02],
    "swipe_velocity_mean":         [450, 30],
    "swipe_velocity_std":          [60, 10],
    "gesture_curvature_mean":      [0.12, 0.03],
    "pinch_zoom_accel_mean":       [0.22, 0.04],
    "tap_duration_mean":           [145, 15],
    "tap_duration_std":            [30, 8],
    # Typing Biometrics
    "inter_key_delay_mean":        [180, 15],
    "inter_key_delay_std":         [25, 5],
    "inter_key_delay_p95":         [280, 20],
    "dwell_time_mean":             [95, 8],
    "dwell_time_std":              [12, 3],
    "error_rate":                  [0.04, 0.01],
    "backspace_frequency":         [2.1, 0.5],
    "typing_burst_count":          [4, 1],
    "typing_burst_duration_mean":  [3200, 400],
    "words_per_minute":            [38, 4],
    # Device Motion
    "accel_x_std":                 [0.18, 0.03],
    "accel_y_std":                 [0.21, 0.04],
    "accel_z_std":                 [0.15, 0.03],
    "gyro_x_std":                  [0.08, 0.02],
    "gyro_y_std":                  [0.09, 0.02],
    "gyro_z_std":                  [0.07, 0.02],
    "device_tilt_mean":            [72, 5],
    "hand_stability_score":        [0.82, 0.05],
    # Navigation Graph
    "screens_visited_count":       [6, 1],
    "navigation_depth_max":        [4, 1],
    "back_navigation_count":       [1.2, 0.5],
    "time_on_dashboard_ms":        [45000, 8000],
    "time_on_transfer_ms":         [28000, 5000],
    "direct_to_transfer":          0.15,
    "form_field_order_entropy":    [0.12, 0.04],
    "session_revisit_count":       [0.8, 0.4],
    "exploratory_ratio":           [0.08, 0.02],
    # Temporal Behavior
    "session_duration_ms":         [240000, 30000],
    "session_duration_z_score":    [0.0, 1.0],
    "time_of_day_hour":            {"choices": [9, 10, 18, 19, 20]},
    "time_to_submit_otp_ms":       [8500, 2000],
    "click_speed_mean":            [380, 40],
    "click_speed_std":             [95, 20],
    "form_submit_speed_ms":        [42000, 6000],
    "interaction_pace_ratio":      [1.0, 0.12],
    # Device Context
    "is_new_device":               0,
    "device_fingerprint_delta":    [0.05, 0.01],
    "timezone_changed":            0,
    "os_version_changed":          0,
    # Device Trust Context
    "device_class_known":          1,
    "device_session_count":        [8, 2],
    "device_class_switch":         0,
    "is_known_fingerprint":        1,
    "time_since_last_seen_hours":  [18, 6],
    # Mouse Biometrics (near-zero for mobile — user is on phone)
    "mouse_movement_entropy":      [0.05, 0.02],
    "mouse_speed_cv":              [0.08, 0.03],
    "scroll_wheel_event_count":    [0.2, 0.1]
  },

  "scenario_1": {
    # New Phone + SIM — attacker on own device
    "inter_key_delay_mean":        [310, 60],
    "inter_key_delay_std":         [90, 20],
    "inter_key_delay_p95":         [520, 80],
    "dwell_time_mean":             [140, 30],
    "words_per_minute":            [22, 5],
    "swipe_velocity_mean":         [280, 80],
    "hand_stability_score":        [0.51, 0.10],
    "session_duration_ms":         [95000, 10000],
    "time_of_day_hour":            {"choices": [2, 3]},
    "direct_to_transfer":          1,
    "exploratory_ratio":           [0.35, 0.08],
    "time_to_submit_otp_ms":       [2100, 300],
    "interaction_pace_ratio":      [1.8, 0.2],
    "is_new_device":               1,
    "device_fingerprint_delta":    [0.94, 0.03],
    "device_class_known":          0,
    "device_session_count":        0,
    "device_class_switch":         0,
    "is_known_fingerprint":        0,
    "time_since_last_seen_hours":  [9999, 1]
  },

  "scenario_2": {
    # Laptop + OTP SIM — device modality switch (no touch events)
    "inter_key_delay_mean":        [145, 20],
    "swipe_velocity_mean":         0,
    "swipe_velocity_std":          0,
    "tap_pressure_mean":           0,
    "tap_pressure_std":            0,
    "tap_duration_mean":           0,
    "tap_duration_std":            0,
    "gesture_curvature_mean":      0,
    "accel_x_std":                 0,
    "accel_y_std":                 0,
    "accel_z_std":                 0,
    "gyro_x_std":                  0,
    "gyro_y_std":                  0,
    "gyro_z_std":                  0,
    "hand_stability_score":        0,
    "device_tilt_mean":            0,
    "form_field_order_entropy":    [0.85, 0.10],
    "session_duration_ms":         [110000, 15000],
    "time_of_day_hour":            {"choices": [1, 2, 3]},
    "direct_to_transfer":          1,
    "is_new_device":               1,
    "device_fingerprint_delta":    [0.97, 0.02],
    "exploratory_ratio":           [0.28, 0.07],
    "time_to_submit_otp_ms":       [3200, 500],
    "device_class_switch":         1,
    "device_class_known":          0,
    "is_known_fingerprint":        0,
    "device_session_count":        0,
    "mouse_movement_entropy":      [2.8, 0.3],
    "mouse_speed_cv":              [0.65, 0.10],
    "scroll_wheel_event_count":    [12, 3]
  },

  "scenario_3": {
    # Bot / Automated — inhuman consistency
    "inter_key_delay_mean":        [42, 2],
    "inter_key_delay_std":         [1.5, 0.3],
    "inter_key_delay_p95":         [45, 1],
    "dwell_time_mean":             [20, 1],
    "dwell_time_std":              [0.5, 0.1],
    "click_speed_std":             [0.8, 0.2],
    "time_to_submit_otp_ms":       [800, 50],
    "interaction_pace_ratio":      [0.05, 0.01],
    "typing_burst_count":          1,
    "error_rate":                  0,
    "direct_to_transfer":          1,
    "session_duration_ms":         [45000, 3000],
    "session_duration_z_score":    [-3.0, 0.2],
    "exploratory_ratio":           [0.01, 0.005],
    "is_new_device":               1,
    "words_per_minute":            [95, 3],
    "form_field_order_entropy":    [0.01, 0.005],
    "device_class_known":          0,
    "device_session_count":        0,
    "is_known_fingerprint":        0,
    "time_since_last_seen_hours":  [9999, 1],
    "mouse_movement_entropy":      [0.02, 0.005],
    "mouse_speed_cv":              [0.01, 0.003],
    "scroll_wheel_event_count":    0
  },

  "scenario_4": {
    # Same Device Takeover — hardest case, known device
    "inter_key_delay_mean":        [210, 35],
    "session_duration_ms":         [95000, 8000],
    "session_duration_z_score":    [-2.4, 0.3],
    "direct_to_transfer":          1,
    "time_of_day_hour":            {"choices": [3, 4]},
    "time_to_submit_otp_ms":       [3800, 600],
    "exploratory_ratio":           [0.18, 0.05],
    "is_new_device":               0,
    "device_fingerprint_delta":    [0.08, 0.02],
    "hand_stability_score":        [0.71, 0.08],
    "device_class_known":          1,
    "device_session_count":        [8, 2],
    "is_known_fingerprint":        1,
    "device_class_switch":         0,
    "time_since_last_seen_hours":  [18, 6]
  },

  "scenario_5": {
    # Credential stuffing + fleet — same device, multiple accounts
    "inter_key_delay_mean":        [290, 55],
    "is_new_device":               1,
    "device_fingerprint_delta":    [0.91, 0.03],
    "direct_to_transfer":          1,
    "time_to_submit_otp_ms":       [1800, 200],
    "session_duration_ms":         [75000, 8000],
    "device_class_known":          0,
    "device_session_count":        0,
    "is_known_fingerprint":        0,
    "time_since_last_seen_hours":  [9999, 1],
    "_fleet_fingerprint":          "ATTACKER_DEVICE_FLEET_001"
  }
}
