import { Hero } from '@/components/sections/Hero';
import { Features } from '@/components/sections/Features';
import { CTA } from '@/components/sections/CTA';

export default function HomePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Hero />
      <Features />
      <CTA />
    </div>
  );
}