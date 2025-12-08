import React from 'react';

const apiBase = (import.meta.env.VITE_API_BASE_URL as string) || '/api';

export default function LegalIndexPage() {
  const links = [
    { label: 'Privacy Policy', slug: 'privacy' },
    { label: 'Terms of Service', slug: 'terms' },
    { label: 'Cookies', slug: 'cookies' },
    { label: 'Imprint', slug: 'imprint' },
  ];

  return (
    <div style={{ padding: '16px' }}>
      <h1>Legal</h1>
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {links.map((l) => (
          <li key={l.slug} style={{ marginBottom: '8px' }}>
            <a href={`${apiBase}/legal/${l.slug}`} target="_blank" rel="noreferrer noopener">
              {l.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
