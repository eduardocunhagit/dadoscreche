import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Frente 2 | Mapa de demanda por creches',
  description: 'Modelo explicável de escolha, concorrência e validação fora da amostra para a SME Rio.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="pt-BR"><body>{children}</body></html>;
}
