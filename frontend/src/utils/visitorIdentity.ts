import { createFingerprintBundle, getDeviceInfo, type DeviceInfo } from "./fingerprint";

const VISITOR_KEY = "fraud_pdf_visitor_id";
const SESSION_KEY = "fraud_pdf_session_id";

export type VisitorIdentity = {
  localStorageId: string;
  sessionId: string;
  fingerprintHash: string;
  deviceProfileHash: string;
  canvasHash: string;
  webglHash: string;
  audioHash?: string;
  deviceInfo: DeviceInfo;
  automationSignals: {
    webdriver: boolean;
    plugins_count: number;
    cookies_enabled: boolean;
    local_storage_available: boolean;
    session_storage_available: boolean;
    do_not_track: string;
  };
};

function randomId(prefix: string) {
  return `${prefix}-${crypto.randomUUID()}`;
}

function getOrCreateStorageId(storage: Storage, key: string, prefix: string) {
  const existing = storage.getItem(key);
  if (existing) return existing;
  const value = randomId(prefix);
  storage.setItem(key, value);
  return value;
}

export async function getVisitorIdentity(): Promise<VisitorIdentity> {
  const deviceInfo = await getDeviceInfo();
  const bundle = await createFingerprintBundle(deviceInfo);
  return {
    localStorageId: getOrCreateStorageId(localStorage, VISITOR_KEY, "visitor"),
    sessionId: getOrCreateStorageId(sessionStorage, SESSION_KEY, "session"),
    fingerprintHash: bundle.fingerprintHash,
    deviceProfileHash: bundle.deviceProfileHash,
    canvasHash: bundle.canvasHash,
    webglHash: bundle.webglHash,
    audioHash: bundle.audioHash,
    deviceInfo,
    automationSignals: {
      webdriver: deviceInfo.webdriver,
      plugins_count: deviceInfo.plugins_count,
      cookies_enabled: deviceInfo.cookies_enabled,
      local_storage_available: deviceInfo.local_storage_available,
      session_storage_available: deviceInfo.session_storage_available,
      do_not_track: deviceInfo.do_not_track || "unspecified",
    },
  };
}

export async function getIdentityHeaders(): Promise<Record<string, string>> {
  const identity = await getVisitorIdentity();
  return {
    "X-Anon-Id": identity.localStorageId,
    "X-Device-Fingerprint": identity.fingerprintHash,
    "X-Visitor-Id": identity.localStorageId,
    "X-Session-Id": identity.sessionId,
  };
}
