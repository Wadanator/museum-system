import {
  CloudFog,
  Fan,
  Flame,
  Gauge,
  Lamp,
  Layers,
  Lightbulb,
  Sparkles,
  Wind,
  Zap,
} from 'lucide-react';

const DEVICE_ICONS = {
  effect: Sparkles,
  effects: Sparkles,
  fan: Fan,
  fire: Flame,
  fog: CloudFog,
  group: Layers,
  lamp: Lamp,
  light: Lightbulb,
  motor: Gauge,
  relay: Zap,
  smoke: CloudFog,
  vent: Wind,
  wind: Wind,
};

const normalize = (value) => (
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
);

const inferIconKey = (device = {}) => {
  const explicitIcon = normalize(device.icon);
  if (DEVICE_ICONS[explicitIcon]) return explicitIcon;

  const lookupText = normalize([
    device.id,
    device.name,
    device.topic,
    device.type,
    device.deviceType,
  ].filter(Boolean).join(' '));

  if (lookupText.includes('smoke') || lookupText.includes('dym')) return 'smoke';
  if (lookupText.includes('fire') || lookupText.includes('ohen')) return 'fire';
  if (lookupText.includes('fan')) return 'fan';
  if (lookupText.includes('wind') || lookupText.includes('vent')) return 'wind';
  if (lookupText.includes('group') || lookupText.includes('blikanie')) return 'group';
  if (
    lookupText.includes('light')
    || lookupText.includes('svetlo')
    || lookupText.includes('ziarov')
    || lookupText.includes('edizon')
  ) {
    return 'light';
  }
  if (device.type === 'motor' || device.deviceType === 'motor') return 'motor';
  if (device.type === 'light' || device.deviceType === 'light') return 'light';
  return 'relay';
};

export const getDeviceIconComponent = (device) => (
  DEVICE_ICONS[inferIconKey(device)] || Zap
);

export default function DeviceIcon({ device, size = 64, strokeWidth = 1.4, ...props }) {
  const Icon = getDeviceIconComponent(device);
  return <Icon size={size} strokeWidth={strokeWidth} {...props} />;
}
