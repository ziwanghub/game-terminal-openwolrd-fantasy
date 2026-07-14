import React from 'react';
import { bookingConfig, handleBooking } from '../config/booking';
import { useLanguage } from '../hooks/useLanguage';

export function Footer() { 
  const { content } = useLanguage() as any;
  return (
    <footer className="bg-[var(--warm-charcoal)] text-white py-16">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8 grid md:grid-cols-3 gap-12">
        <div>
          <h3 className="text-2xl tracking-wide mb-4">{content.footer.brand}</h3>
          <p className="text-sm opacity-80 leading-relaxed">{content.footer.tagline}</p>
        </div>
        <div>
          <h4 className="mb-4 tracking-wide">{content.footer.quickLinks}</h4>
          <p className="text-sm opacity-80 leading-loose flex flex-col items-start gap-1">
            <span>{content.footer.navServices}</span>
            <span>{content.footer.navTeam}</span>
            <button onClick={handleBooking} className={`transition-colors text-left focus:outline-none ${bookingConfig.mode === 'line' ? 'hover:text-[#06C755]' : 'hover:text-[var(--warm-caramel)]'}`}>
              {bookingConfig.mode === 'line' ? content.footer.btnBookLine : content.footer.btnBookWeb}
            </button>
          </p>
        </div>
        <div>
          <h4 className="mb-4 tracking-wide">{content.footer.connect}</h4>
          <p className="text-sm opacity-80 leading-loose">LINE: @serenity-wellness</p>
        </div>
      </div>
    </footer>
  ); 
}
