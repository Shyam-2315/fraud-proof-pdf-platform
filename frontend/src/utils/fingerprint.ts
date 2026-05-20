export type DeviceInfo = {
  screen: string;
  available_screen: string;
  screen_width: number;
  screen_height: number;
  available_screen_width: number;
  available_screen_height: number;
  timezone: string;
  timezone_offset: number;
  language: string;
  languages: string[];
  platform: string;
  hardware_concurrency: number;
  device_memory: number;
  touch_support: number;
  color_depth: number;
  pixel_ratio: number;
  cookies_enabled: boolean;
  local_storage_available: boolean;
  session_storage_available: boolean;
  do_not_track: string | null;
  plugins_count: number;
  webdriver: boolean;
};

export type FingerprintBundle = {
  fingerprintHash: string;
  deviceProfileHash: string;
  canvasHash: string;
  webglHash: string;
  audioHash?: string;
};

export async function getDeviceInfo(): Promise<DeviceInfo> {
  return {
    screen: `${window.screen.width}x${window.screen.height}`,
    available_screen: `${window.screen.availWidth}x${window.screen.availHeight}`,
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    available_screen_width: window.screen.availWidth,
    available_screen_height: window.screen.availHeight,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    timezone_offset: new Date().getTimezoneOffset(),
    language: navigator.language,
    languages: Array.from(navigator.languages || []),
    platform: navigator.platform,
    hardware_concurrency: navigator.hardwareConcurrency || 0,
    device_memory: Number((navigator as Navigator & { deviceMemory?: number }).deviceMemory || 0),
    touch_support: navigator.maxTouchPoints || 0,
    color_depth: window.screen.colorDepth,
    pixel_ratio: window.devicePixelRatio || 1,
    cookies_enabled: navigator.cookieEnabled,
    local_storage_available: storageAvailable("localStorage"),
    session_storage_available: storageAvailable("sessionStorage"),
    do_not_track: navigator.doNotTrack || null,
    plugins_count: navigator.plugins ? navigator.plugins.length : 0,
    webdriver: Boolean((navigator as Navigator & { webdriver?: boolean }).webdriver),
  };
}

export async function createFingerprintHash(deviceInfo: DeviceInfo): Promise<string> {
  const source = stableStringify(deviceInfo);
  return hashText(source);
}

export async function createFingerprintBundle(deviceInfo: DeviceInfo): Promise<FingerprintBundle> {
  const canvasHash = await getCanvasHash();
  const webglHash = await getWebglHash();
  const audioHash = await getAudioHash();
  const profileSource = {
    screen_width: deviceInfo.screen_width,
    screen_height: deviceInfo.screen_height,
    available_screen_width: deviceInfo.available_screen_width,
    available_screen_height: deviceInfo.available_screen_height,
    timezone: deviceInfo.timezone,
    timezone_offset: deviceInfo.timezone_offset,
    language: deviceInfo.language,
    languages: deviceInfo.languages,
    platform: deviceInfo.platform,
    hardware_concurrency: deviceInfo.hardware_concurrency,
    device_memory: deviceInfo.device_memory,
    touch_support: deviceInfo.touch_support,
    color_depth: deviceInfo.color_depth,
    pixel_ratio: deviceInfo.pixel_ratio,
  };
  return {
    fingerprintHash: await hashText(stableStringify({ ...deviceInfo, canvasHash, webglHash, audioHash })),
    deviceProfileHash: await hashText(stableStringify(profileSource)),
    canvasHash,
    webglHash,
    audioHash,
  };
}

async function hashText(source: string): Promise<string> {
  const bytes = new TextEncoder().encode(source);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  return `{${Object.entries(value as Record<string, unknown>)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableStringify(item)}`)
    .join(",")}}`;
}

function storageAvailable(type: "localStorage" | "sessionStorage") {
  try {
    const storage = window[type];
    const key = "__pdfcraft_storage_test__";
    storage.setItem(key, key);
    storage.removeItem(key);
    return true;
  } catch {
    return false;
  }
}

async function getCanvasHash() {
  try {
    const canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 60;
    const ctx = canvas.getContext("2d");
    if (!ctx) return hashText("canvas-unavailable");
    ctx.textBaseline = "top";
    ctx.font = "16px Arial";
    ctx.fillStyle = "#f3f6fb";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#123456";
    ctx.fillText("PDFCraft fingerprint", 12, 12);
    ctx.strokeStyle = "#bc4521";
    ctx.arc(180, 30, 18, 0, Math.PI * 2);
    ctx.stroke();
    return hashText(canvas.toDataURL());
  } catch {
    return hashText("canvas-error");
  }
}

async function getWebglHash() {
  try {
    const canvas = document.createElement("canvas");
    const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
    if (!gl) return hashText("webgl-unavailable");
    const webgl = gl as WebGLRenderingContext;
    const debugInfo = webgl.getExtension("WEBGL_debug_renderer_info");
    const vendor = debugInfo ? webgl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL) : webgl.getParameter(webgl.VENDOR);
    const renderer = debugInfo ? webgl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL) : webgl.getParameter(webgl.RENDERER);
    return hashText(`${vendor}|${renderer}`);
  } catch {
    return hashText("webgl-error");
  }
}

async function getAudioHash() {
  try {
    const AudioContextClass = window.OfflineAudioContext || (window as Window & { webkitOfflineAudioContext?: typeof OfflineAudioContext }).webkitOfflineAudioContext;
    if (!AudioContextClass) return undefined;
    const context = new AudioContextClass(1, 5000, 44100);
    const oscillator = context.createOscillator();
    const compressor = context.createDynamicsCompressor();
    oscillator.type = "triangle";
    oscillator.frequency.value = 10000;
    compressor.threshold.value = -50;
    compressor.knee.value = 40;
    compressor.ratio.value = 12;
    compressor.attack.value = 0;
    compressor.release.value = 0.25;
    oscillator.connect(compressor);
    compressor.connect(context.destination);
    oscillator.start(0);
    const buffer = await context.startRendering();
    const samples = Array.from(buffer.getChannelData(0).slice(0, 64)).join(",");
    return hashText(samples);
  } catch {
    return undefined;
  }
}
