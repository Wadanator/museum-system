import { useMemo } from 'react';
import { useDevices } from './useDevices';
import { useMedia } from './useMedia';

/**
 * Transforms raw devices + media into flat, normalised palette items
 * ready for EditorPalette to render.
 */
export function useDevicePalette() {
  const { motors, relays, loading: devLoading, error: devError } = useDevices();
  const { audios, videos, playMediaFile, isLoading: mediaLoading } = useMedia();

  const motorItems = useMemo(
    () => motors.map((d) => ({
      id: d.id,
      label: d.name,
      topic: d.topic,
      deviceType: 'motor',
      quickMessages: ['ON', 'OFF'],
    })),
    [motors]
  );

  const relayItems = useMemo(
    () => relays.map((d) => ({
      id: d.id,
      label: d.name,
      topic: d.topic,
      deviceType: d.id?.includes('light') ? 'light' : 'relay',
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
    () => videos.map((f) => ({
      name: f.name,
      insertMessage: `PLAY_VIDEO:${f.name}`,
    })),
    [videos]
  );

  return {
    motorItems,
    relayItems,
    audioItems,
    videoItems,
    loading: devLoading || mediaLoading,
    devError,
    playMediaFile,
  };
}
