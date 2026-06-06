import React from 'react';
import { Plus } from 'lucide-react';
import ActionEditor from './ActionEditor';
import { createEmptyAction } from '../../../utils/generators';

const ActionListEditor = ({ actions, onChange, globalPrefix }) => {
  const addAction = () => {
    const newAction = createEmptyAction();
    onChange([...actions, newAction]);
  };

  const updateAction = (index, updates) => {
    const newActions = [...actions];
    newActions[index] = { ...newActions[index], ...updates };
    onChange(newActions);
  };

  const deleteAction = (index) => {
    onChange(actions.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-end">
        <button
          onClick={addAction}
          className="px-2 py-1 bg-green-600 hover:bg-green-700 rounded text-xs flex items-center gap-1 transition uppercase font-bold tracking-wider"
          title="Pridať akciu"
        >
          <Plus size={12} /> Pridať Akciu
        </button>
      </div>

      {actions.length === 0 && (
        <div className="text-center p-3 border border-dashed border-gray-600 rounded text-gray-500 text-sm italic">
          Žiadne akcie.
        </div>
      )}

      {actions.map((action, index) => (
        <ActionEditor
          key={action.id || index}
          action={action}
          onChange={(updated) => updateAction(index, updated)}
          onDelete={() => deleteAction(index)}
          globalPrefix={globalPrefix}
        />
      ))}
    </div>
  );
};

export default ActionListEditor;