import { io } from 'socket.io-client';

// Automatická detekcia URL
const SOCKET_URL = import.meta.env.DEV ? 'http://localhost:5000' : '/';

export const socket = io(SOCKET_URL, {
  autoConnect: true,
  reconnection: true,
});