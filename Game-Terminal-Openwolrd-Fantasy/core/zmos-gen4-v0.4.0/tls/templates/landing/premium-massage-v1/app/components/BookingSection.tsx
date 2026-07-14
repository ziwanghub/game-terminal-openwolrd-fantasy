import React from 'react';
import { useLanguage } from '../hooks/useLanguage';

export function BookingSection() { 
  const { content } = useLanguage() as any;

  return (
    <section id="book" className="py-20 lg:py-28 bg-[var(--warm-cream)]">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8">
        <div className="text-center space-y-4 mb-12 sm:mb-16">
          <h2 className="text-3xl lg:text-4xl text-[var(--warm-charcoal)] font-normal tracking-tight">
            {content.bookingChannels.title}
          </h2>
          <p className="text-lg text-[var(--dark-taupe)] max-w-2xl mx-auto leading-relaxed">
            {content.bookingChannels.subtitle}
          </p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-8 max-w-5xl mx-auto">
          {content.bookingChannels.channels.map((channel: any) => (
            <div 
              key={channel.id} 
              className="bg-white rounded-2xl p-4 sm:p-6 lg:p-8 shadow-[var(--shadow-soft)] hover:shadow-[var(--shadow-premium)] transition-all flex flex-col items-center justify-center text-center space-y-4 sm:space-y-6 group border border-[var(--border)] border-opacity-30"
            >
              <div className="w-full aspect-square bg-[var(--soft-beige)] rounded-xl flex items-center justify-center p-3 sm:p-4 overflow-hidden">
                <img 
                  src={channel.qrImage} 
                  alt={`${channel.name} QR Code`} 
                  className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-500 ease-out"
                />
              </div>
              <div className="space-y-1 sm:space-y-2">
                <h3 className="text-base sm:text-lg font-medium text-[var(--warm-charcoal)] tracking-wide group-hover:text-[var(--warm-caramel)] transition-colors">
                  {channel.name}
                </h3>
                {channel.label && (
                  <p className="text-[10px] sm:text-xs tracking-wider uppercase text-[var(--dark-taupe)] opacity-80 font-medium">
                    {channel.label}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  ); 
}
