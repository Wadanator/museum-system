import { useEffect, useState } from 'react';

function getCurrentTheme() {
  if (typeof document === 'undefined') {
    return 'light';
  }

  const attrTheme = document.documentElement.getAttribute('data-theme');
  return attrTheme === 'dark' ? 'dark' : 'light';
}

export default function useDocumentTheme() {
  const [theme, setTheme] = useState(getCurrentTheme);

  useEffect(() => {
    if (typeof document === 'undefined') {
      return undefined;
    }

    const root = document.documentElement;
    const observer = new MutationObserver(() => {
      setTheme(getCurrentTheme());
    });

    observer.observe(root, {
      attributes: true,
      attributeFilter: ['data-theme'],
    });

    return () => {
      observer.disconnect();
    };
  }, []);

  return theme;
}
