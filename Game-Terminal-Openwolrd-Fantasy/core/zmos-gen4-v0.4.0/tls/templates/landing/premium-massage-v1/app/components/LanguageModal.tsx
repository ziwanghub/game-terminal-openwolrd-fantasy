import React, { useState, useEffect } from 'react';
import { useLanguage, LanguageType } from '../hooks/useLanguage';

export function LanguageModal() {
  const { setLanguage } = useLanguage() as any;
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Only show if the user hasn't actively locked an initial language decision in cache
    const hasLang = localStorage.getItem('serenity_lang');
    if (!hasLang) {
      setIsOpen(true);
      // Optional: lock body scroll if desired, but overlay handles blocking clicks
      document.body.style.overflow = 'hidden';
    }
  }, []);

  if (!isOpen) return null;

  const handleSelect = (lang: LanguageType) => {
    setLanguage(lang);
    setIsOpen(false);
    document.body.style.overflow = 'unset';
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[var(--deep-cocoa)]/60 backdrop-blur-sm p-4 sm:p-6 transition-all duration-700 opacity-100">
      <div className="bg-[var(--warm-cream)] rounded-[2rem] w-full max-w-[360px] p-8 sm:p-10 shadow-2xl flex flex-col items-center text-center transform transition-transform duration-700 ease-out scale-100 border border-[var(--border)] border-opacity-30">
        <h2 className="text-[26px] text-[var(--warm-charcoal)] font-normal mb-3 tracking-tight">
          Choose your language
        </h2>
        <p className="text-[13px] text-[var(--dark-taupe)] leading-relaxed mb-8 max-w-[260px]">
          Please select your preferred language to continue.
        </p>
        
        <div className="w-full space-y-3 sm:space-y-4">
          <button 
            onClick={() => handleSelect('en')}
            className="w-full py-4 px-6 bg-white border border-[var(--border)] border-opacity-40 rounded-2xl text-[var(--warm-charcoal)] text-[15px] font-medium tracking-widest hover:border-[var(--warm-caramel)] hover:text-[var(--warm-caramel)] hover:shadow-md transition-all duration-300 shadow-sm"
          >
            English
          </button>
          <button 
            onClick={() => handleSelect('th')}
            className="w-full py-4 px-6 bg-white border border-[var(--border)] border-opacity-40 rounded-2xl text-[var(--warm-charcoal)] text-[15px] font-medium tracking-wider hover:border-[var(--warm-caramel)] hover:text-[var(--warm-caramel)] hover:shadow-md transition-all duration-300 shadow-sm"
          >
            ไทย
          </button>
          <button 
            onClick={() => handleSelect('zh')}
            className="w-full py-4 px-6 bg-white border border-[var(--border)] border-opacity-40 rounded-2xl text-[var(--warm-charcoal)] text-[15px] font-medium tracking-[0.15em] hover:border-[var(--warm-caramel)] hover:text-[var(--warm-caramel)] hover:shadow-md transition-all duration-300 shadow-sm"
          >
            简体中文
          </button>
        </div>
      </div>
    </div>
  );
}
