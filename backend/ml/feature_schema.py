FEATURE_NAMES = [
    # Touch Dynamics (8 features)
    "tap_pressure_mean",          # mean force sensor value across session taps
    "tap_pressure_std",           # std dev of tap pressure
    "swipe_velocity_mean",        # mean pixels/ms across all swipe events
    "swipe_velocity_std",
    "gesture_curvature_mean",     # mean deviation from straight line in swipes
    "pinch_zoom_accel_mean",      # mean acceleration of pinch-to-zoom gestures
    "tap_duration_mean",          # mean time finger is on screen per tap (ms)
    "tap_duration_std",

    # Typing Biometrics (10 features)
    "inter_key_delay_mean",       # mean time between consecutive keypresses (ms)
    "inter_key_delay_std",
    "inter_key_delay_p95",        # 95th percentile — catches burst typing
    "dwell_time_mean",            # mean time each key is held down (ms)
    "dwell_time_std",
    "error_rate",                 # backspace count / total keystrokes
    "backspace_frequency",        # backspaces per minute
    "typing_burst_count",         # number of distinct typing bursts per session
    "typing_burst_duration_mean", # mean duration of each burst (ms)
    "words_per_minute",           # estimated WPM from session

    # Device Motion (8 features)
    "accel_x_std",                # std dev of X-axis accelerometer during typing
    "accel_y_std",
    "accel_z_std",
    "gyro_x_std",                 # std dev of gyroscope X during session
    "gyro_y_std",
    "gyro_z_std",
    "device_tilt_mean",           # mean device angle from vertical (degrees)
    "hand_stability_score",       # inverse of motion variance — higher = steadier

    # Navigation Graph (9 features)
    "screens_visited_count",      # total unique screens visited
    "navigation_depth_max",       # deepest nav stack depth reached
    "back_navigation_count",      # number of back button presses
    "time_on_dashboard_ms",       # time spent on home/dashboard screen
    "time_on_transfer_ms",        # time spent on transfer/payment screen
    "direct_to_transfer",         # 1 if went straight to transfer, 0 otherwise
    "form_field_order_entropy",   # entropy of field completion order (0=linear)
    "session_revisit_count",      # number of times a screen was revisited
    "exploratory_ratio",          # back_navigations / total navigations

    # Temporal Behavior (8 features)
    "session_duration_ms",        # total session length
    "session_duration_z_score",   # z-score vs user's historical mean
    "time_of_day_hour",           # hour of session start (0-23)
    "time_to_submit_otp_ms",      # time between OTP received and submitted
    "click_speed_mean",           # mean ms between consecutive UI interactions
    "click_speed_std",
    "form_submit_speed_ms",       # time from first field focus to submit
    "interaction_pace_ratio",     # actual pace / historical mean pace

    # Device Context (4 features — categorical, session-level)
    "is_new_device",              # 1 if device fingerprint not in user's allowlist
    "device_fingerprint_delta",   # cosine distance from nearest known device
    "timezone_changed",           # 1 if timezone differs from last 5 sessions
    "os_version_changed",         # 1 if OS version changed since last session

    # Device Trust Context (5 features — NEW: multi-device / PC support)
    "device_class_known",         # 1 if user has prior sessions on this device class (mobile/desktop)
    "device_session_count",       # count of prior sessions on this exact device fingerprint
    "device_class_switch",        # 1 if current class differs from user's dominant class last 30 days
    "is_known_fingerprint",       # 1 if fingerprint in device_registry with session_count >= 3
    "time_since_last_seen_hours", # hours since this device was last used (0 if never seen)

    # Desktop Mouse Biometrics (3 features — NEW: always 0.0 on mobile/touch device)
    "mouse_movement_entropy",     # Shannon entropy of mouse path (0.0 on mobile always)
    "mouse_speed_cv",             # coeff of variation of mouse speed (bots ~0.0, humans 0.3-0.8)
    "scroll_wheel_event_count",   # count of scroll wheel events (impossible on mobile = 0 always)
]

assert len(FEATURE_NAMES) == 55
