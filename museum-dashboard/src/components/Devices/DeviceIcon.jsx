import {
  CloudFog,
  Fan,
  Flame,
  Gauge,
  Lamp,
  Layers,
  Lightbulb,
  Sparkles,
  SquareSplitVertical,
  Wind,
  Zap,
} from 'lucide-react';

const normalize = (value) => (
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
);

const inferIconKey = (device = {}) => {
  const explicitIcon = normalize(device.icon);
  if ([
    'effect',
    'effects',
    'fan',
    'fire',
    'fog',
    'group',
    'lamp',
    'light',
    'motor',
    'relay',
    'smoke',
    'vent',
    'wind',
    'window',
  ].includes(explicitIcon)) {
    return explicitIcon;
  }

  const lookupText = normalize([
    device.id,
    device.name,
    device.topic,
    device.type,
    device.deviceType,
  ].filter(Boolean).join(' '));

  if (lookupText.includes('smoke') || lookupText.includes('dym')) return 'smoke';
  if (lookupText.includes('fire') || lookupText.includes('ohen')) return 'fire';
  if (lookupText.includes('window') || lookupText.includes('okno')) return 'window';
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
  if (device.type === 'window' || device.deviceType === 'window') return 'window';
  if (device.type === 'motor' || device.deviceType === 'motor') return 'motor';
  if (device.type === 'light' || device.deviceType === 'light') return 'light';
  return 'relay';
};

export default function DeviceIcon({ device, size = 64, strokeWidth = 1.4, ...props }) {
  const iconProps = { size, strokeWidth, ...props };

  switch (inferIconKey(device)) {
    case 'effect':
    case 'effects':
      return <Sparkles {...iconProps} />;
    case 'fan':
      return <Fan {...iconProps} />;
    case 'fire':
      return <Flame {...iconProps} />;
    case 'fog':
    case 'smoke':
      return <CloudFog {...iconProps} />;
    case 'group':
      return <Layers {...iconProps} />;
    case 'lamp':
      return <Lamp {...iconProps} />;
    case 'light':
      return <Lightbulb {...iconProps} />;
    case 'motor':
      return <Gauge {...iconProps} />;
    case 'window':
      return <SquareSplitVertical {...iconProps} />;
    case 'vent':
    case 'wind':
      return <Wind {...iconProps} />;
    case 'relay':
    default:
      return <Zap {...iconProps} />;
  }
}

