import { useContext } from 'react';
import { RuntimeContext } from './RuntimeContextValue';

export const useRuntime = () => {
  const context = useContext(RuntimeContext);
  if (!context) {
    throw new Error('useRuntime must be used within RuntimeProvider');
  }
  return context;
};
