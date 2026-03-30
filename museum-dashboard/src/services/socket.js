import { io } from 'socket.io-client';

// Priority: explicit env URL -> same-origin (works with proxy / reverse proxy)
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || undefined;

// Načítanie tokenu pre socket spojenie
const auth = localStorage.getItem('auth_header');

export const socket = io(SOCKET_URL, {
  autoConnect: true,
  reconnection: true,
  path: '/socket.io',
  extraHeaders: auth ? {
    Authorization: auth
  } : {}
});