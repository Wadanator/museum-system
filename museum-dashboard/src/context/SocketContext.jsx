import { createContext, useContext, useEffect, useState } from 'react';
import { socket } from '../services/socket';
import toast from 'react-hot-toast';

const SocketContext = createContext();

export function SocketProvider({ children }) {
  const [isConnected, setIsConnected] = useState(socket.connected);

  useEffect(() => {
    function onConnect() {
      setIsConnected(true);
      toast.success('Pripojené k serveru', { id: 'socket-status' });
    }

    function onDisconnect() {
      setIsConnected(false);
      toast.error('Odpojené od servera', { id: 'socket-status' });
    }

    socket.on('connect', onConnect);
    socket.on('disconnect', onDisconnect);

    // Inicialny stav
    setIsConnected(socket.connected);

    return () => {
      socket.off('connect', onConnect);
      socket.off('disconnect', onDisconnect);
    };
  }, []);

  return (
    <SocketContext.Provider value={{ socket, isConnected }}>
      {children}
    </SocketContext.Provider>
  );
}

// Vlastný hook pre jednoduché použitie
export const useSocket = () => useContext(SocketContext);