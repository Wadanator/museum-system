#!/usr/bin/env python3
"""mpv command-line construction."""

from typing import List, Sequence


def build_mpv_command(
    *,
    idle_image: str,
    ipc_socket: str,
    vo: str,
    gpu_context: str,
    hwdec: str,
    hwdec_codecs: str,
    framedrop: str,
    extra_args: Sequence[str],
) -> List[str]:
    """
    Build the mpv command line used by the persistent playback process.

    Args:
        idle_image: Image shown while no video is playing.
        ipc_socket: Unix IPC socket path used for mpv commands.
        vo: mpv video output backend.
        gpu_context: mpv GPU context, useful for DRM/KMS console output.
        hwdec: mpv hardware decoder mode.
        hwdec_codecs: Comma-separated codec allow-list for hardware decoding.
        framedrop: mpv framedrop strategy.
        extra_args: Additional raw mpv arguments from configuration.

    Returns:
        list[str]: Complete command including executable and idle image.
    """
    cmd = [
        'mpv',
        '--fs',
        '--no-osc',
        '--no-osd-bar',
    ]

    if vo:
        cmd.append(f'--vo={vo}')
    if gpu_context:
        cmd.append(f'--gpu-context={gpu_context}')
    if hwdec:
        cmd.append(f'--hwdec={hwdec}')
    if hwdec_codecs:
        cmd.append(f'--hwdec-codecs={hwdec_codecs}')
    if framedrop:
        cmd.append(f'--framedrop={framedrop}')

    cmd.extend([
        '--image-display-duration=inf',
        '--cache=yes',
        '--demuxer-max-bytes=50M',
        '--demuxer-readahead-secs=30',
        '--loop-file=inf',
        '--idle=yes',
        '--vd-lavc-threads=0',
        '--msg-level=all=info',
        '--no-input-default-bindings',
        '--input-conf=/dev/null',
        '--no-terminal',
        f'--input-ipc-server={ipc_socket}',
    ])

    cmd.extend(extra_args)
    cmd.append(idle_image)
    return cmd
