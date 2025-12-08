import { PropsWithChildren } from 'react';
import { Link } from 'react-router-dom';

export function PublicShell({ children }: PropsWithChildren<{}>) {
  return <div style={{ maxWidth: 920, margin: '0 auto', padding: 16 }}>{children}</div>;
}