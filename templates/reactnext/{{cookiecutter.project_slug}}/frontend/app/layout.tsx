import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Header } from '@/components/layout/Header';
import { Footer } from '@/components/layout/Footer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: {
    template: '%s | {{cookiecutter.project_name}}',
    default: '{{cookiecutter.project_name}}',
  },
  description: '{{cookiecutter.description}}',
  keywords: ['startup', 'ai', 'react', 'nextjs'],
  authors: [{ name: '{{cookiecutter.author_name}}' }],
  creator: '{{cookiecutter.author_name}}',
  publisher: '{{cookiecutter.project_name}}',
  metadataBase: new URL(process.env.NEXTAUTH_URL || 'http://localhost:{{cookiecutter.base_port}}'),
  alternates: {
    canonical: '/',
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    url: process.env.NEXTAUTH_URL || 'http://localhost:{{cookiecutter.base_port}}',
    siteName: '{{cookiecutter.project_name}}',
    title: '{{cookiecutter.project_name}}',
    description: '{{cookiecutter.description}}',
    images: [
      {
        url: '/og-image.png',
        width: 1200,
        height: 630,
        alt: '{{cookiecutter.project_name}}',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: '{{cookiecutter.project_name}}',
    description: '{{cookiecutter.description}}',
    images: ['/og-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  verification: {
    // google: 'google-site-verification-code',
    // yandex: 'yandex-verification-code',
    // yahoo: 'yahoo-site-verification-code',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </Providers>
      </body>
    </html>
  );
}