export interface Scenario {
  id: number;
  name: string;
  strength: 'STRONG' | 'MODERATE' | 'CONTROL';
  isAttack: boolean;
}

export interface ScenarioResult {
  scenarioId: number;
  scenarioName: string;
  score: number;
  detected: boolean;
  time: string;
  result: 'BLOCKED' | 'STEP-UP' | 'ALLOWED' | 'ALL FROZEN';
  legacyResult: string;
}

export interface FeatureRow {
  name: string;
  baseline: number;
  session: number;
  zScore: number;
  flagged: boolean;
}

export type StepStatus = 'pending' | 'ready' | 'active' | 'done';

export const SCENARIOS: Scenario[] = [
  { id: 1, name: 'New Phone + SIM', strength: 'STRONG', isAttack: true },
  { id: 2, name: 'Laptop + OTP SIM', strength: 'STRONG', isAttack: true },
  { id: 3, name: 'Bot Automation', strength: 'STRONG', isAttack: true },
  { id: 4, name: 'Same Device Takeover', strength: 'MODERATE', isAttack: true },
  { id: 5, name: 'Credential Stuffing', strength: 'STRONG', isAttack: true },
  { id: 6, name: 'Pre-Auth SIM Probe', strength: 'STRONG', isAttack: true },
  { id: 7, name: 'Legitimate User', strength: 'CONTROL', isAttack: false },
];

export const MOCK_FEATURES: FeatureRow[] = [
  { name: 'device_fingerprint_hash', baseline: 0.92, session: 0.11, zScore: 4.2, flagged: true },
  { name: 'sim_iccid_match', baseline: 1.0, session: 0.0, zScore: 5.8, flagged: true },
  { name: 'typing_cadence_ms', baseline: 142, session: 312, zScore: 3.9, flagged: true },
  { name: 'touch_pressure_avg', baseline: 0.67, session: 0.0, zScore: 4.1, flagged: true },
  { name: 'screen_resolution', baseline: 1080, session: 1440, zScore: 2.8, flagged: true },
  { name: 'gps_lat_delta', baseline: 0.001, session: 12.4, zScore: 6.1, flagged: true },
  { name: 'gps_lon_delta', baseline: 0.002, session: 8.7, zScore: 5.3, flagged: true },
  { name: 'session_time_hour', baseline: 14, session: 3, zScore: 3.2, flagged: true },
  { name: 'app_version_match', baseline: 1.0, session: 0.0, zScore: 3.0, flagged: true },
  { name: 'network_carrier', baseline: 0.95, session: 0.1, zScore: 3.8, flagged: true },
  { name: 'accelerometer_pattern', baseline: 0.88, session: 0.22, zScore: 2.5, flagged: true },
  { name: 'gyroscope_signature', baseline: 0.76, session: 0.31, zScore: 2.1, flagged: true },
  { name: 'battery_drain_rate', baseline: 2.1, session: 1.8, zScore: 0.4, flagged: false },
  { name: 'ambient_light_level', baseline: 340, session: 280, zScore: 0.7, flagged: false },
  { name: 'wifi_ssid_familiar', baseline: 0.9, session: 0.0, zScore: 3.5, flagged: true },
  { name: 'bluetooth_devices_count', baseline: 3, session: 0, zScore: 2.2, flagged: true },
  { name: 'os_version', baseline: 14.2, session: 13.1, zScore: 1.8, flagged: false },
  { name: 'keyboard_language', baseline: 1.0, session: 1.0, zScore: 0.0, flagged: false },
  { name: 'scroll_velocity_avg', baseline: 450, session: 890, zScore: 2.9, flagged: true },
  { name: 'tap_accuracy_ratio', baseline: 0.94, session: 0.71, zScore: 2.3, flagged: true },
  { name: 'clipboard_paste_count', baseline: 0.2, session: 3.0, zScore: 4.5, flagged: true },
  { name: 'font_rendering_hash', baseline: 0.99, session: 0.45, zScore: 3.1, flagged: true },
  { name: 'webgl_fingerprint', baseline: 0.97, session: 0.12, zScore: 4.8, flagged: true },
  { name: 'canvas_fingerprint', baseline: 0.98, session: 0.15, zScore: 4.6, flagged: true },
  { name: 'audio_context_hash', baseline: 0.96, session: 0.33, zScore: 3.7, flagged: true },
  { name: 'timezone_offset', baseline: 330, session: 330, zScore: 0.0, flagged: false },
  { name: 'locale_string', baseline: 1.0, session: 1.0, zScore: 0.0, flagged: false },
  { name: 'installed_plugins', baseline: 5, session: 12, zScore: 2.4, flagged: true },
  { name: 'cpu_cores', baseline: 8, session: 4, zScore: 1.9, flagged: false },
  { name: 'memory_gb', baseline: 8, session: 16, zScore: 1.5, flagged: false },
  { name: 'connection_type', baseline: 0.85, session: 0.9, zScore: 0.3, flagged: false },
  { name: 'dns_resolution_ms', baseline: 45, session: 120, zScore: 2.6, flagged: true },
  { name: 'tls_fingerprint', baseline: 0.93, session: 0.41, zScore: 3.3, flagged: true },
  { name: 'http_header_order', baseline: 0.91, session: 0.55, zScore: 2.0, flagged: true },
  { name: 'cookie_consent_time', baseline: 2.3, session: 0.1, zScore: 3.4, flagged: true },
  { name: 'mouse_movement_entropy', baseline: 0.82, session: 0.0, zScore: 4.9, flagged: true },
  { name: 'form_fill_speed_ms', baseline: 8500, session: 120, zScore: 5.5, flagged: true },
  { name: 'page_focus_ratio', baseline: 0.95, session: 0.3, zScore: 3.6, flagged: true },
  { name: 'referrer_consistency', baseline: 1.0, session: 0.0, zScore: 4.0, flagged: true },
  { name: 'session_depth_pages', baseline: 5, session: 1, zScore: 2.7, flagged: true },
  { name: 'login_attempt_velocity', baseline: 0.1, session: 3.2, zScore: 5.1, flagged: true },
  { name: 'captcha_solve_time_ms', baseline: 4200, session: 890, zScore: 3.9, flagged: true },
  { name: 'ip_reputation_score', baseline: 0.92, session: 0.15, zScore: 4.4, flagged: true },
  { name: 'asn_consistency', baseline: 1.0, session: 0.0, zScore: 5.0, flagged: true },
  { name: 'vpn_detection', baseline: 0.0, session: 1.0, zScore: 4.7, flagged: true },
  { name: 'proxy_detection', baseline: 0.0, session: 0.8, zScore: 3.8, flagged: true },
  { name: 'emulator_detection', baseline: 0.0, session: 0.0, zScore: 0.0, flagged: false },
];
