import React from 'react';
import { useLanguage } from '../hooks/useLanguage';
import { bookingConfig, handleBooking } from '../config/booking';

export function SignatureSection() { 
  const { content } = useLanguage();

  return (
    <section className="py-20 lg:py-28 bg-[var(--warm-cream)]">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        <div className="relative aspect-[4/5] rounded-2xl bg-[var(--soft-beige)] flex items-center justify-center overflow-hidden">
          <img 
            src={content.signature.image} 
            alt={content.signature.title} 
            className="w-full h-full object-cover object-center" 
          />
        </div>
        <div className="space-y-8">
          <p className="text-sm tracking-widest uppercase text-[var(--warm-caramel)]">{content.signature.tag}</p>
          <h2 className="text-3xl lg:text-4xl text-[var(--warm-charcoal)] font-normal">{content.signature.title}</h2>
          <p className="text-lg text-[var(--dark-taupe)] leading-relaxed">{content.signature.description}</p>
          <p className="text-3xl text-[var(--warm-caramel)]">{content.signature.price}</p>
          <button 
            onClick={handleBooking}
            className={`w-full sm:w-auto px-8 py-4 border rounded-full transition-all duration-300 font-medium ${bookingConfig.mode === 'line' ? 'bg-transparent text-[var(--warm-caramel)] border-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white' : 'bg-[var(--warm-caramel)] text-white border-transparent hover:bg-[var(--soft-bronze)]'}`}
          >
            {bookingConfig.mode === 'line' ? content.signature.cta : content.signature.ctaWeb}
          </button>
        </div>
      </div>
    </section>
  ); 
}
