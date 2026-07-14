import React from 'react';
import { Header } from '@/components/Header';
import { HeroSection } from '@/components/HeroSection';
import { ServicesSection } from '@/components/ServicesSection';
import { TrustSection } from '@/components/TrustSection';
import { SignatureSection } from '@/components/SignatureSection';
import { TeamSection } from '@/components/TeamSection';
import { CoverageSection } from '@/components/CoverageSection';
import { BookingSection } from '@/components/BookingSection';
import { Footer } from '@/components/Footer';
import { LanguageModal } from '@/components/LanguageModal';
import { useLanguage } from '@/hooks/useLanguage';

export default function App() {
  const { config } = useLanguage() as any;
  const features = config?.features || {};

  return (
    <div className="min-h-screen flex flex-col font-sans w-full overflow-x-hidden">
      <LanguageModal />
      <Header />
      <main className="flex-grow">
        <HeroSection />
        <TrustSection />
        <ServicesSection />
        <SignatureSection />
        {features.staff?.visible && <TeamSection />}
        <CoverageSection />
        {features.booking?.visible && <BookingSection />}
      </main>
      <Footer />
    </div>
  );
}

