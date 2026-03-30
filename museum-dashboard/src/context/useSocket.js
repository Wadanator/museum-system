import { useContext } from 'react';
import { SocketContext } from './SocketContextValue';

export const useSocket = () => useContext(SocketContext);