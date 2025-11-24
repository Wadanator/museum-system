import Editor from '@monaco-editor/react';

export default function JsonEditor({ value, onChange, isLoading = false }) {
  
  // Funkcia, ktorá sa zavolá pri zmene kódu
  const handleEditorChange = (value, event) => {
    onChange(value);
  };

  // Konfigurácia editora (vypnutie zbytočností pre čistejší vzhľad)
  const editorOptions = {
    minimap: { enabled: false },      // Vypne malú mapu kódu vpravo
    fontSize: 14,                     // Veľkosť písma
    lineNumbers: 'on',                // Čísla riadkov
    roundedSelection: false,
    scrollBeyondLastLine: false,
    readOnly: false,
    automaticLayout: true,            // Automaticky sa prispôsobí veľkosti okna
    formatOnPaste: true,              // Formátuje kód pri vložení
    formatOnType: true,               // Formátuje kód pri písaní
  };

  return (
    <div className="code-editor-wrapper" style={{ position: 'relative', height: '100%' }}>
      {/* Loading overlay rieši samotný Monaco editor, ale ak chceš vlastný: */}
      {isLoading && (
        <div className="editor-loading-overlay" style={{ zIndex: 100 }}>
          <span className="loading-label">Načítavam...</span>
        </div>
      )}
      
      <Editor
        height="100%"
        defaultLanguage="json"
        value={value || ''}
        onChange={handleEditorChange}
        options={editorOptions}
        theme="light"
        loading={<div className="loading-label">Načítavam editor...</div>}
      />
    </div>
  );
}