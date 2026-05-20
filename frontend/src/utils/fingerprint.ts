export type DeviceInfo = {
  screen: string;
  timezone: string;
  language: string;
  platform: string;
  hardware_concurrency: number;
  device_memory: number;
  touch_support: number;
};

export async function getDeviceInfo(): Promise<DeviceInfo> {
  return {
    screen: `${window.screen.width}x${window.screen.height}`,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    language: navigator.language,
    platform: navigator.platform,
    hardware_concurrency: navigator.hardwareConcurrency || 0,
    device_memory: Number((navigator as Navigator & { deviceMemory?: number }).deviceMemory || 0),
    touch_support: navigator.maxTouchPoints || 0,
  };
}

export async function createFingerprintHash(deviceInfo: DeviceInfo): Promise<string> {
  const source = [
    deviceInfo.screen,
    deviceInfo.timezone,
    deviceInfo.language,
    deviceInfo.platform,
    deviceInfo.hardware_concurrency,
    deviceInfo.device_memory,
    deviceInfo.touch_support,
  ].join("|");
  const bytes = new TextEncoder().encode(source);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}
