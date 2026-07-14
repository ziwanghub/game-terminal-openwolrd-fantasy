import React from 'react';
import { useLanguage } from '../hooks/useLanguage';
import { bookingConfig, handleBooking } from '../config/booking';

export function ServicesSection() {
  const { content } = useLanguage();

  return (
    <section id="services" className="py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8">
        <div className="text-center mb-16 space-y-4">
          <p className="text-sm tracking-widest uppercase text-[var(--warm-caramel)]">{content.services.sectionSubtitle}</p>
          <h2 className="text-3xl lg:text-4xl tracking-tight text-[var(--warm-charcoal)] font-normal">
            {content.services.sectionTitle}
          </h2>
        </div>
        
        <div className="grid md:grid-cols-2 gap-8 lg:gap-10">
          {content.services.items.map((svc) => (
            <div key={svc.id} className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-[var(--shadow-premium)] transition-all group">
              <div className="relative aspect-[16/10] bg-[var(--soft-beige)] flex items-center justify-center overflow-hidden">
                {svc.tag && (
                  <div className="absolute top-4 left-4 bg-white/95 backdrop-blur-sm px-4 py-1.5 rounded-full shadow-sm text-[10px] tracking-widest uppercase text-[var(--warm-caramel)] font-medium z-10">
                    {svc.tag}
                  </div>
                )}
                <img 
                  src={svc.image} 
                  alt={svc.title}
                  className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-700 ease-in-out"
                />
              </div>
              <div className="p-8 space-y-8 flex flex-col h-full bg-white">
                <div className="space-y-6 flex-grow">
                  <div className="space-y-3">
                    <h3 className="text-xl tracking-tight text-[var(--warm-charcoal)] group-hover:text-[var(--warm-caramel)] transition-colors">{svc.title}</h3>
                    <p className="leading-relaxed text-[var(--dark-taupe)]">{svc.desc}</p>
                  </div>
                  
                  {/* Soft Premium Pricing List */}
                  <div className="pt-4 space-y-1">
                    {svc.options.map((opt: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center py-2 border-b border-[var(--border)] border-opacity-30 last:border-0">
                        <span className="text-sm text-[var(--dark-taupe)] tracking-wide">{opt.duration}</span>
                        <span className="text-sm text-[var(--warm-caramel)] font-medium tracking-wide">{opt.price}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="pt-4 mt-auto w-full">
                  <button 
                    onClick={handleBooking}
                    className={`w-full px-4 sm:px-8 py-3.5 border rounded-full text-sm tracking-wide transition-all duration-300 font-medium ${bookingConfig.mode === 'line' ? 'bg-transparent text-[var(--warm-caramel)] border-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white' : 'bg-[var(--warm-caramel)] text-white border-transparent hover:bg-[var(--soft-bronze)]'}`}
                  >
                    {bookingConfig.mode === 'line' ? content.services.ctaButton : content.services.ctaButtonWeb}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
