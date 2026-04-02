import { useEffect, useState } from 'react';
import { socket } from '../services/socket';
import toast from 'react-hot-toast';
import { SocketContext } from './SocketContextValue';
import { useAuth } from './useAuth';

export function SocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(socket.connected);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
      toast.success('Pripojené k serveru', { id: 'socket-status' });
    }

    function onDisconnect() {
      setIsConnected(false);
      toast.error('Odpojené od servera', { id: 'socket-status' });
    }

    function onConnectError() {
      toast.error('Chyba pripojenia k serveru', { id: 'socket-error' });
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);
    socket.on('connect_error', onConnectError);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
      socket.off('connect_error', onConnectError);
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      if (socket.connected) {
        socket.disconnect();
      }
      return;
    }

    const authToken = localStorage.getItem('auth_header');
    socket.auth = authToken ? { token: authToken } : {};

    if (!socket.connected) {
      socket.connect();
    }
  }, [isAuthenticated]);

  return (
    <SocketContext.Provider value={{ socket, isConnected }}>
      {children}
    </SocketContext.Provider>
  );
}