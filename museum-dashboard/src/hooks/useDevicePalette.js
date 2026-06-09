import { useMemo } from 'react';
import { useDevices } from './useDevices';
import { useMedia } from './useMedia';
import { buildMotorOnCommand, normalizeMotorSpeed } from '../utils/deviceCommands';

const VIDEO_EXTENSIONS = new Set(['.mp4', '.avi', '.mkv', '.mov', '.webm']);
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg']);

const extensionOf = (name = '') => {
  const index = name.lastIndexOf('.');
  return index === -1 ? '' : name.slice(index).toLowerCase();
};

/**
 * Transforms raw devices + media into flat, normalised palette items
 * ready for EditorPalette to render.
 */
export function useDevicePalette() {
  const { motors, relays, loading: devLoading, error: devError } = useDevices();
  const { audios, videos, playMediaFile, isLoading: mediaLoading } = useMedia();

  const motorItems = useMemo(
    () => motors.map((d) => {
      const speed = normalizeMotorSpeed(d.speed);
      return {
        id: d.id,
        label: d.name,
        topic: d.topic,
        icon: d.icon,
        deviceType: 'motor',
        defaultMessage: buildMotorOnCommand(speed, 'L'),
        // ON:<speed>:<dir>[:<rampMs>] | OFF | SPEED:<0-100> | DIR:L/R
        quickMessages: [
          buildMotorOnCommand(speed, 'L'),
          buildMotorOnCommand(speed, 'R'),
          'OFF',
          `SPEED:${speed}`,
          'DIR:L',
          'DIR:R',
        ],
      };
    }),
    [motors]
  );

  const relayItems = useMemo(
    () => relays.map((d) => ({
      id: d.id,
      label: d.name,
      topic: d.topic,
      icon: d.icon,
      deviceType: d.id?.includes('light') ? 'light' : 'relay',
      defaultMessage: 'ON',
      quickMessages: ['ON', 'OFF'],
    })),
    [relays]
  );

  const audioItems = useMemo(
    () => audios.map((f) => ({
      name: f.name,
      insertMessage: `PLAY:${f.name}:1.0`,
    })),
    [audios]
  );

  const videoItems = useMemo(
    () => videos
      .filter((f) => VIDEO_EXTENSIONS.has(extensionOf(f.name)))
      .map((f) => ({
        name: f.name,
        insertMessage: `PLAY_VIDEO:${f.name}`,
      })),
    [videos]
  );

  const imageItems = useMemo(
    () => videos
      .filter((f) => IMAGE_EXTENSIONS.has(extensionOf(f.name)))
      .map((f) => ({
        name: f.name,
        insertMessage: `SHOW:${f.name}`,
      })),
    [videos]
  );

  return {
    motorItems,
    relayItems,
    audioItems,
    videoItems,
    imageItems,
    loading: devLoading || mediaLoading,
    devError,
    playMediaFile,
  };
}
