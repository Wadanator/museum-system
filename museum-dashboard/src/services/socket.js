import { io } from 'socket.io-client';

// Automatická detekcia URL
const SOCKET_URL = import.meta.env.DEV ? 'http://localhost:5000' : '/';

// Načítanie tokenu pre socket spojenie
const auth = localStorage.getItem('auth_header');

export const socket = io(SOCKET_URL, {
  autoConnect: true,
  reconnection: true,
  extraHeaders: auth ? {
    Authorization: auth
  } : {}
});