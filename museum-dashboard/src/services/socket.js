import { io } from 'socket.io-client';

// Priority: explicit env URL -> same-origin (works with proxy / reverse proxy)
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || undefined;

// Browser sends Authorization automatically for same-origin requests after login.
// Keep client config simple and predictable.

export const socket = io(SOCKET_URL, {
  autoConnect: false,
  reconnection: true,
  reconnectionDelay: 500,
  reconnectionDelayMax: 5000,
  reconnectionAttempts: Infinity,
  path: '/socket.io',
  transports: ['websocket', 'polling']
});
