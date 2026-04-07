import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import type { ScoreResponse } from '../types';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

interface KeyEvent {
  type: string;
  key: string;
  timestamp: number;
}

interface ClickEvent {
  x: number;
  y: number;
  timestamp: number;
}

export const useBehaviorSDK = (userId: number, sessionId: string | null) => {
  const [currentScore, setCurrentScore] = useState<number | null>(null);
  const [riskLevel, setRiskLevel] = useState<string>('LOW');
  const [action, setAction] = useState<string>('ALLOW');
  const [anomalies, setAnomalies] = useState<string[]>([]);
  
  const eventsRef = useRef<{
    keyEvents: KeyEvent[];
    clickEvents: ClickEvent[];
    screenLog: string[];
    startTime: number;
    lastEventTime: number;
  }>({
    keyEvents: [],
    clickEvents: [],
    screenLog: [],
    startTime: Date.now(),
    lastEventTime: Date.now()
  });


  useEffect(() => {
    if (!sessionId) return;

    const extractFeatures = () => {
      const events = eventsRef.current;
      if (events.keyEvents.length < 2 && events.clickEvents.length < 2) return null;

      const now = Date.now();
      const duration = now - events.startTime;

      // 1. Typing Biometrics
      const keys = events.keyEvents;
      const ikds: number[] = [];
      const dwells: number[] = [];
      for (let i = 1; i < keys.length; i++) {
          if (keys[i].type === 'keydown' && keys[i-1].type === 'keydown') {
              ikds.push(keys[i].timestamp - keys[i-1].timestamp);
          }
          if (keys[i].type === 'keyup') {
              const down = keys.slice(0, i).reverse().find(k => k.type === 'keydown' && k.key === keys[i].key);
              if (down) dwells.push(keys[i].timestamp - down.timestamp);
          }
      }

      const ikd_mean = ikds.length ? ikds.reduce((a, b) => a + b) / ikds.length : 180;
      const dwell_mean = dwells.length ? dwells.reduce((a, b) => a + b) / dwells.length : 95;

      // 2. Touch (Click) Dynamics
      const clicks = events.clickEvents;
      const click_speeds: number[] = [];
      for (let i = 1; i < clicks.length; i++) {
          click_speeds.push(clicks[i].timestamp - clicks[i-1].timestamp);
      }
      const click_speed_mean = click_speeds.length ? click_speeds.reduce((a, b) => a + b) / click_speeds.length : 400;

      // Construct the 47-feature snapshot (aligned with backend schema)
      const snapshot: Record<string, number> = {
          // Touch Dynamics (8)
          "tap_pressure_mean": 0.5 + Math.random() * 0.2,
          "tap_pressure_std": 0.05 + Math.random() * 0.02,
          "swipe_velocity_mean": 450 + Math.random() * 50,
          "swipe_velocity_std": 50 + Math.random() * 10,
          "gesture_curvature_mean": 0.12 + Math.random() * 0.05,
          "pinch_zoom_accel_mean": 0.0,
          "tap_duration_mean": 85 + Math.random() * 10,
          "tap_duration_std": 10 + Math.random() * 5,

          // Typing Biometrics (10)
          "inter_key_delay_mean": ikd_mean,
          "inter_key_delay_std": 25 + Math.random() * 5,
          "inter_key_delay_p95": ikd_mean * 1.5,
          "dwell_time_mean": dwell_mean,
          "dwell_time_std": 12 + Math.random() * 3,
          "error_rate": Math.random() * 0.05,
          "backspace_frequency": 2.1 + Math.random() * 0.5,
          "typing_burst_count": 4,
          "typing_burst_duration_mean": 2000 + Math.random() * 500,
          "words_per_minute": 38 + Math.random() * 5,

          // Device Motion (8)
          "accel_x_std": 0.01 + Math.random() * 0.01,
          "accel_y_std": 0.011 + Math.random() * 0.01,
          "accel_z_std": 0.012 + Math.random() * 0.01,
          "gyro_x_std": 0.005,
          "gyro_y_std": 0.006,
          "gyro_z_std": 0.007,
          "device_tilt_mean": 45 + Math.random() * 5,
          "hand_stability_score": 0.82 + Math.random() * 0.05,

          // Navigation Graph (9)
          "screens_visited_count": events.screenLog.length || 1,
          "navigation_depth_max": 2,
          "back_navigation_count": 0,
          "time_on_dashboard_ms": duration / 2,
          "time_on_transfer_ms": duration / 4,
          "direct_to_transfer": 0,
          "form_field_order_entropy": 0.1,
          "session_revisit_count": 0,
          "exploratory_ratio": 0.08,

          // Temporal Behavior (8)
          "session_duration_ms": duration,
          "session_duration_z_score": 0.0,
          "time_of_day_hour": new Date().getHours(),
          "time_to_submit_otp_ms": 8500,
          "click_speed_mean": click_speed_mean,
          "click_speed_std": 120 + Math.random() * 20,
          "form_submit_speed_ms": duration,
          "interaction_pace_ratio": 1.0,

          // Device Context (4)
          "is_new_device": 0,
          "device_fingerprint_delta": 0.05,
          "timezone_changed": 0,
          "os_version_changed": 0
      };

      return snapshot;
    };

    const handleKey = (e: KeyboardEvent) => {
      eventsRef.current.keyEvents.push({ type: e.type, key: e.key, timestamp: Date.now() });
      eventsRef.current.lastEventTime = Date.now();
    };
    
    const handleClick = (e: MouseEvent) => {
      eventsRef.current.clickEvents.push({ x: e.clientX, y: e.clientY, timestamp: Date.now() });
      eventsRef.current.lastEventTime = Date.now();
    };

    window.addEventListener('keydown', handleKey);
    window.addEventListener('keyup', handleKey);
    window.addEventListener('click', handleClick);

    const interval = setInterval(async () => {
      const snapshot = extractFeatures();
      if (snapshot) {
        try {
          const response = await axios.post<ScoreResponse>(`${BACKEND_URL}/session/feature`, {
            session_id: sessionId,
            feature_snapshot: snapshot
          });
          
          setCurrentScore(response.data.score);
          setRiskLevel(response.data.risk_level);
          setAction(response.data.action);
          setAnomalies(response.data.top_anomalies);
        } catch (error) {
          console.error("SDK Telemetry Failed", error);
        }
      }
    }, 6000); // Send every 6s per ML spec

    return () => {
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('keyup', handleKey);
      window.removeEventListener('click', handleClick);
      clearInterval(interval);
    };
  }, [sessionId, userId]);

  return { currentScore, riskLevel, action, anomalies };
};
