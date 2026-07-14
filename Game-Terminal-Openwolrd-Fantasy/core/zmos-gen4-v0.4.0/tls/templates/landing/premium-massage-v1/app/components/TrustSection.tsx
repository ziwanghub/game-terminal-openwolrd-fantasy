import React from 'react';
import { useLanguage } from '../hooks/useLanguage';

export function TrustSection() { 
  const { content } = useLanguage();

  return (
    <section className="bg-white py-20 lg:py-24">
      <div className="max-w-4xl mx-auto px-5 sm:px-6 lg:px-8 text-center space-y-6">
        <h2 className="text-2xl lg:text-3xl tracking-tight text-[var(--warm-charcoal)] font-normal">
          {content.trust.title}
        </h2>
        <p className="text-lg leading-relaxed max-w-2xl mx-auto text-[var(--dark-taupe)]">
          {content.trust.description}
        </p>
      </div>
    </section>
  ); 
}
