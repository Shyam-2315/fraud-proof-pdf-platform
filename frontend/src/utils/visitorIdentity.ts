import { createFingerprintHash, getDeviceInfo, type DeviceInfo } from "./fingerprint";

const VISITOR_KEY = "fraud_pdf_visitor_id";
const SESSION_KEY = "fraud_pdf_session_id";

export type VisitorIdentity = {
  localStorageId: string;
  sessionId: string;
  fingerprintHash: string;
  deviceInfo: DeviceInfo;
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
  return {
    localStorageId: getOrCreateStorageId(localStorage, VISITOR_KEY, "visitor"),
    sessionId: getOrCreateStorageId(sessionStorage, SESSION_KEY, "session"),
    fingerprintHash: await createFingerprintHash(deviceInfo),
    deviceInfo,
  };
}

export async function getIdentityHeaders(): Promise<Record<string, string>> {
  const identity = await getVisitorIdentity();
  return {
    "X-Device-Fingerprint": identity.fingerprintHash,
    "X-Visitor-Id": identity.localStorageId,
    "X-Session-Id": identity.sessionId,
  };
}
