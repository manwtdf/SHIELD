import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import type { ScoreResponse } from '../types';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

interface KeyEvent { type: string; key: string; timestamp: number; }
interface ClickEvent { x: number; y: number; timestamp: number; }
interface TouchEventLog { x: number; y: number; timestamp: number; pressure: number; type: string }
interface MouseMoveEvent { x: number; y: number; timestamp: number; }

// Math helpers
const mean = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0;
const stdDev = (arr: number[]) => {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  return Math.sqrt(arr.reduce((sq, n) => sq + Math.pow(n - m, 2), 0) / (arr.length - 1));
};
const p95 = (arr: number[]) => {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a,b) => a-b);
  return sorted[Math.floor(sorted.length * 0.95)] || sorted[sorted.length-1];
};

export const useBehaviorSDK = (userId: number, sessionId: string | null) => {
  const [currentScore, setCurrentScore] = useState<number | null>(null);
  const [riskLevel, setRiskLevel] = useState<string>('LOW');
  const [action, setAction] = useState<string>('ALLOW');
  const [anomalies, setAnomalies] = useState<string[]>([]);
  
  const eventsRef = useRef<{
    keyEvents: KeyEvent[];
    clickEvents: ClickEvent[];
    touchEvents: TouchEventLog[];
    mouseMove: MouseMoveEvent[];
    scrollCount: number;
    screenLog: string[];
    startTime: number;
    lastEventTime: number;
    backspaceCount: number;
  }>({
    keyEvents: [],
    clickEvents: [],
    touchEvents: [],
    mouseMove: [],
    scrollCount: 0,
    screenLog: [],
    startTime: Date.now(),
    lastEventTime: Date.now(),
    backspaceCount: 0
  });

  const extractFeatures = useCallback(() => {
    const events = eventsRef.current;
    const now = Date.now();
    const duration = now - events.startTime;

    // Type
    const keys = events.keyEvents;
    const ikds: number[] = [];
    const dwells: number[] = [];
    let burstCount = 0;
    for (let i = 1; i < keys.length; i++) {
        if (keys[i].type === 'keydown' && keys[i-1].type === 'keydown') {
            const diff = keys[i].timestamp - keys[i-1].timestamp;
            ikds.push(diff);
            if (diff < 200) burstCount++;
        }
        if (keys[i].type === 'keyup') {
            const down = keys.slice(0, i).reverse().find(k => k.type === 'keydown' && k.key === keys[i].key);
            if (down) dwells.push(keys[i].timestamp - down.timestamp);
        }
    }

    // Touch / Clicks
    const clicks = events.clickEvents;
    const clickSpeeds: number[] = [];
    for (let i = 1; i < clicks.length; i++) {
      clickSpeeds.push(clicks[i].timestamp - clicks[i-1].timestamp);
    }

    // Touch Velocity
    const touches = events.touchEvents;
    const tapDurs: number[] = [];
    const swipeVels: number[] = [];
    let currentTouchStart: TouchEventLog | null = null;
    for (const t of touches) {
      if (t.type === 'touchstart') currentTouchStart = t;
      if (t.type === 'touchend' && currentTouchStart) {
        const dur = t.timestamp - currentTouchStart.timestamp;
        const dist = Math.hypot(t.x - currentTouchStart.x, t.y - currentTouchStart.y);
        tapDurs.push(dur);
        if (dist > 20 && dur > 0) swipeVels.push(dist / dur * 1000); // px/sec
      }
    }

    // Mouse Entropy
    const mves = events.mouseMove;
    const mouseSpeeds: number[] = [];
    let xBins = new Set<number>();
    let yBins = new Set<number>();
    for (let i = 1; i < mves.length; i++) {
      const dt = mves[i].timestamp - mves[i-1].timestamp;
      const dx = mves[i].x - mves[i-1].x;
      const dy = mves[i].y - mves[i-1].y;
      if (dt > 0) mouseSpeeds.push(Math.hypot(dx, dy) / dt);
      xBins.add(Math.floor(mves[i].x / 20)); // spatial binning
      yBins.add(Math.floor(mves[i].y / 20));
    }
    const mouseMax = mouseSpeeds.length ? Math.max(...mouseSpeeds) : 1;
    const mouseEntropy = mouseSpeeds.length ? (xBins.size * yBins.size) / (mouseSpeeds.length + 1) : 0;

    // Compute Baseline Defaults or Actual Metrics
    const ikdM = ikds.length ? mean(ikds) : 180;
    const ikdS = ikds.length ? stdDev(ikds) : 25;
    const dwlM = dwells.length ? mean(dwells) : 95;
    
    const snapshot: Record<string, number> = {
        // Touch Dynamics (8)
        "tap_pressure_mean": 0.5, // Not reliably exposed on Web APIs without Pen API
        "tap_pressure_std": 0.05,
        "swipe_velocity_mean": tapDurs.length ? mean(swipeVels) : 0,
        "swipe_velocity_std": tapDurs.length ? stdDev(swipeVels) : 0,
        "gesture_curvature_mean": 0.1,
        "pinch_zoom_accel_mean": 0.0,
        "tap_duration_mean": tapDurs.length ? mean(tapDurs) : 85,
        "tap_duration_std": tapDurs.length ? stdDev(tapDurs) : 10,

        // Typing Biometrics (10)
        "inter_key_delay_mean": ikdM,
        "inter_key_delay_std": ikdS,
        "inter_key_delay_p95": ikds.length ? p95(ikds) : ikdM * 1.5,
        "dwell_time_mean": dwlM,
        "dwell_time_std": dwells.length ? stdDev(dwells) : 12,
        "error_rate": events.backspaceCount / (keys.length || 1),
        "backspace_frequency": events.backspaceCount,
        "typing_burst_count": burstCount,
        "typing_burst_duration_mean": burstCount > 0 ? mean(ikds.filter(d=>d<200)) : 0,
        "words_per_minute": keys.length ? (keys.length / 5) / (duration / 60000) : 0,

        // Device Motion (8) Defaults to 0 on web without gyro permissions
        "accel_x_std": 0.01, "accel_y_std": 0.011, "accel_z_std": 0.012,
        "gyro_x_std": 0.005, "gyro_y_std": 0.006, "gyro_z_std": 0.007,
        "device_tilt_mean": 45, "hand_stability_score": 0.85,

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
        "time_to_submit_otp_ms": 8500, // Typically measured on OTP page specific event
        "click_speed_mean": clickSpeeds.length ? mean(clickSpeeds) : 400,
        "click_speed_std": clickSpeeds.length ? stdDev(clickSpeeds) : 120,
        "form_submit_speed_ms": duration,
        "interaction_pace_ratio": 1.0,

        // Device Context (4)
        "is_new_device": 0,
        "device_fingerprint_delta": 0.05,
        "timezone_changed": 0,
        "os_version_changed": 0,

        // Device Trust Context (5)
        "device_class_known": navigator.maxTouchPoints > 0 ? 1 : 0,
        "device_session_count": 5,
        "device_class_switch": 0,
        "is_known_fingerprint": 1,
        "time_since_last_seen_hours": 1.2,

        // Desktop Mouse Biometrics (3)
        "mouse_movement_entropy": mouseEntropy,
        "mouse_speed_cv": mouseSpeeds.length ? stdDev(mouseSpeeds) / mouseMax : 0,
        "scroll_wheel_event_count": events.scrollCount
    };

    return snapshot;
  }, []);

  const captureAndFeedData = useCallback(async () => {
    if (!sessionId) return;
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
  }, [sessionId, extractFeatures]);

  useEffect(() => {
    if (!sessionId) return;

    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Backspace') eventsRef.current.backspaceCount++;
      eventsRef.current.keyEvents.push({ type: e.type, key: e.key, timestamp: Date.now() });
      eventsRef.current.lastEventTime = Date.now();
    };
    
    const handleClick = (e: MouseEvent) => {
      eventsRef.current.clickEvents.push({ x: e.clientX, y: e.clientY, timestamp: Date.now() });
      eventsRef.current.lastEventTime = Date.now();
    };

    const handleTouch = (e: TouchEvent) => {
      if (!e.touches.length) return;
      eventsRef.current.touchEvents.push({
        type: e.type, x: e.touches[0].clientX, y: e.touches[0].clientY,
        timestamp: Date.now(), pressure: (e.touches[0] as any).force || 0.5
      });
      eventsRef.current.lastEventTime = Date.now();
    }

    const handleWheel = () => { eventsRef.current.scrollCount++; }
    
    // Throttle mousemove to save memory
    let lastMove = 0;
    const handleMouseMove = (e: MouseEvent) => {
      if (Date.now() - lastMove > 50) {
        eventsRef.current.mouseMove.push({ x: e.clientX, y: e.clientY, timestamp: Date.now() });
        lastMove = Date.now();
      }
    };

    window.addEventListener('keydown', handleKey);
    window.addEventListener('keyup', handleKey);
    window.addEventListener('click', handleClick);
    window.addEventListener('touchstart', handleTouch);
    window.addEventListener('touchend', handleTouch);
    window.addEventListener('wheel', handleWheel);
    window.addEventListener('mousemove', handleMouseMove);

    // Keep interval as a fallback for pure passive mode, but allow manual trigger.
    const interval = setInterval(captureAndFeedData, 6000);

    return () => {
      window.removeEventListener('keydown', handleKey);
      window.removeEventListener('keyup', handleKey);
      window.removeEventListener('click', handleClick);
      window.removeEventListener('touchstart', handleTouch);
      window.removeEventListener('touchend', handleTouch);
      window.removeEventListener('wheel', handleWheel);
      window.removeEventListener('mousemove', handleMouseMove);
      clearInterval(interval);
    };
  }, [sessionId, userId, captureAndFeedData]);

  return { currentScore, riskLevel, action, anomalies, captureAndFeedData };
};
