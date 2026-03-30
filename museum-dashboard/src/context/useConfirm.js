import { useContext } from 'react';
import { ConfirmContext } from './ConfirmContextValue';

export const useConfirm = () => useContext(ConfirmContext);