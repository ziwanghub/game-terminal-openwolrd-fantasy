import React, { useState, useEffect } from 'react';
import { bookingConfig, handleBooking } from '../config/booking';
import { useLanguage } from '../hooks/useLanguage';

const SLIDER_IMAGES = [
  { src: '/assets/images/HeroSlid1.jpeg', alt: 'Therapist smiling warmly' },
  { src: '/assets/images/HeroSlid2.jpeg', alt: 'Female client relaxed during massage' },
  { src: '/assets/images/HeroSlid3.jpeg', alt: 'Premium female international client massage' },
  { src: '/assets/images/HeroSlid4.jpeg', alt: 'Male Asian client massage' },
  { src: '/assets/images/HeroSlid5.jpeg', alt: 'Male European client massage' },
  { src: '/assets/images/HeroSlid6.jpeg', alt: 'Male global client massage' },
];

export function HeroSection() {
  const { content } = useLanguage() as any;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [previousIndex, setPreviousIndex] = useState(SLIDER_IMAGES.length - 1);
  const [isHovered, setIsHovered] = useState(false);

  // Soft, continuous visible scene flow (~6.5s per slide)
  useEffect(() => {
    if (isHovered) return;
    const timer = setInterval(() => {
      setPreviousIndex(currentIndex);
      setCurrentIndex((prev) => (prev + 1) % SLIDER_IMAGES.length);
    }, 6500); // Calmer flow
    return () => clearInterval(timer);
  }, [currentIndex, isHovered]);

  return (
    <section className="relative">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8 pt-10 pb-16 sm:pt-14 sm:pb-20 lg:pt-20 lg:pb-28">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <div className="space-y-8">
            <div className="space-y-4">
              <p className="text-sm tracking-widest uppercase text-[var(--warm-caramel)]">
                {content.hero.tag}
              </p>
              <h1 className="text-4xl lg:text-5xl xl:text-6xl leading-tight tracking-tight text-[var(--warm-charcoal)] font-normal whitespace-pre-wrap">
                {content.hero.title}
              </h1>
              <p className="text-lg leading-relaxed max-w-md text-[var(--dark-taupe)]">
                {content.hero.description}
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <button 
                onClick={() => document.getElementById('services')?.scrollIntoView({ behavior: 'smooth' })}
                className="px-8 py-4 bg-[var(--warm-caramel)] text-white rounded-full tracking-wide hover:bg-[var(--soft-bronze)] transition-all duration-300 font-medium"
              >
                {content.hero.btnServices}
              </button>
              <button 
                onClick={handleBooking}
                className={`inline-flex items-center justify-center gap-2 px-8 py-4 border border-[var(--warm-caramel)] rounded-full tracking-wide transition-all duration-300 font-medium ${bookingConfig.mode === 'line' ? 'text-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white' : 'text-[var(--warm-caramel)] hover:bg-[var(--warm-caramel)] hover:text-white'}`}
              >
                {bookingConfig.mode === 'line' && (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
                    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
                  </svg>
                )}
                {bookingConfig.mode === 'line' ? content.hero.btnBookLine : content.hero.btnBookWeb}
              </button>
            </div>
          </div>

          <div 
            className="relative w-full"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            <div className="aspect-[4/5] rounded-2xl overflow-hidden bg-[var(--soft-beige)] shadow-[var(--shadow-premium)] relative">
              {SLIDER_IMAGES.map((img, index) => {
                const isActive = index === currentIndex;
                const isPrev = index === previousIndex;

                let zIndexClass = 'z-0';
                if (isActive) zIndexClass = 'z-20';
                else if (isPrev) zIndexClass = 'z-10';

                // Image drift logic resolving the mechanical 'jolt'
                let transformClasses = 'translate-x-[1%] scale-[1.02] transition-none'; // Hidden state offset right, ready to drift left seamlessly
                if (isActive) {
                  transformClasses = 'translate-x-[-1.5%] scale-[1.02] transition-transform duration-[12000ms] ease-linear';
                } else if (isPrev) {
                  // Keep moving leftwards through the out-transition for fluid flow overlapping
                  transformClasses = 'translate-x-[-3%] scale-[1.02] transition-transform duration-[12000ms] ease-linear'; 
                }

                return (
                  <div 
                    key={img.src}
                    className={`absolute inset-0 transition-opacity duration-[2200ms] ease-in-out ${isActive ? 'opacity-100' : 'opacity-0'} ${zIndexClass}`}
                  >
                    <img 
                      src={img.src} 
                      alt={img.alt} 
                      className={`w-full h-full object-cover origin-center ${transformClasses}`}
                      loading="eager" // Preloading resolves rendering flashes upon slide intersection
                    />
                    {/* Quiet overlay ensuring unity across layers */}
                    <div className="absolute inset-0 bg-gradient-to-t from-[var(--deep-cocoa)]/40 via-[var(--deep-cocoa)]/5 to-transparent mix-blend-multiply" />
                  </div>
                );
              })}
              
              {/* Ultra-minimal 1px indicators removing distraction */}
              <div className="absolute bottom-8 left-0 right-0 z-30 flex justify-center items-center gap-2">
                {SLIDER_IMAGES.map((_, index) => (
                  <button 
                    key={index}
                    onClick={() => setCurrentIndex(index)}
                    className="py-4 px-1 flex items-center justify-center focus:outline-none group"
                    aria-label={`Go to slide ${index + 1}`}
                  >
                    <span className={`block h-[1px] rounded-full transition-all duration-[800ms] ease-out ${
                      index === currentIndex 
                        ? 'bg-white/90 w-8' 
                        : 'bg-white/30 w-4 group-hover:bg-white/60'
                    }`} />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}