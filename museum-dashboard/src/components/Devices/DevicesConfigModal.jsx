import { useEffect, useMemo, useState } from 'react';
import toast from 'react-hot-toast';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import JsonEditor from '../Shared/JsonEditor';

export default function DevicesConfigModal({
  isOpen,
  onClose,
  initialContent,
  onSave,
}) {
  const initialJson = useMemo(
    () => JSON.stringify(initialContent ?? { relays: [], motors: [] }, null, 2),
    [initialContent]
  );

  const [jsonString, setJsonString] = useState(initialJson);
  const [isValid, setIsValid] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setJsonString(initialJson);
      setIsValid(true);
      setIsSaving(false);
    }
  }, [isOpen, initialJson]);

  const handleCodeChange = (value) => {
    const next = value ?? '';
    setJsonString(next);
    try {
      JSON.parse(next);
      setIsValid(true);
    } catch {
      setIsValid(false);
    }
  };

  const handleSave = async () => {
    if (!isValid || isSaving) {
      return;
    }

    try {
      const parsed = JSON.parse(jsonString);
      setIsSaving(true);
      const result = await onSave(parsed);
      if (result?.success) {
        toast.success('Devices konfiguracia ulozena');
        onClose();
      } else {
        toast.error(result?.error || 'Nepodarilo sa ulozit devices konfiguraciu');
      }
    } catch {
      toast.error('JSON nie je validny');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Uprava devices konfiguracie"
      className="large-editor"
      footer={(
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSaving}>Zrusit</Button>
          <Button variant="primary" onClick={handleSave} disabled={!isValid} isLoading={isSaving}>
            Ulozit zmeny
          </Button>
        </>
      )}
    >
      <div style={{ height: 'calc(85vh - 180px)' }}>
        <JsonEditor value={jsonString} onChange={handleCodeChange} />
      </div>
      {!isValid && (
        <p style={{ color: 'var(--danger)', marginTop: '10px' }}>
          Neplatny JSON
        </p>
      )}
    </Modal>
  );
}
