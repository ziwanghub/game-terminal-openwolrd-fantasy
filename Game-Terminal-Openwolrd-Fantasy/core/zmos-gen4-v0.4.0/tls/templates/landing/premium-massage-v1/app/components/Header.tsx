import React, { useState, useEffect, useRef } from 'react';
import { bookingConfig, handleBooking } from '../config/booking';
import { useLanguage } from '../hooks/useLanguage';

export function Header() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [langPopoverOpen, setLangPopoverOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [hidden, setHidden] = useState(false);
  const lastScrollY = useRef(0);
  const { content, currentLang, setLanguage } = useLanguage() as any;

  useEffect(() => {
    const HIDE_THRESHOLD = 60;

    const onScroll = () => {
      const currentY = window.scrollY;
      setScrolled(currentY > 8);

      // Don't hide when mobile menu is open
      if (mobileMenuOpen) {
        lastScrollY.current = currentY;
        return;
      }

      // Always show header near the top
      if (currentY < HIDE_THRESHOLD) {
        setHidden(false);
      } else if (currentY > lastScrollY.current + 5) {
        // Scrolling down — hide (mobile only, CSS handles the breakpoint)
        setHidden(true);
      } else if (currentY < lastScrollY.current - 5) {
        // Scrolling up — reveal
        setHidden(false);
      }

      lastScrollY.current = currentY;
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [mobileMenuOpen]);

  return (
    <>
    <header className={`fixed top-0 left-0 w-full z-50 border-b transition-all duration-300 ${
      hidden ? 'md:translate-y-0 -translate-y-full' : 'translate-y-0'
    } ${
      scrolled 
        ? 'bg-white/98 backdrop-blur-md border-[var(--border)] shadow-[0_2px_20px_rgba(0,0,0,0.04)]' 
        : 'bg-white/95 backdrop-blur-sm border-[var(--border)] border-opacity-60'
    }`}>
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 md:h-20 w-full min-w-0">
          <div className="flex items-center min-w-0 flex-1 pr-2 sm:pr-4">
            <h1 className="text-xl sm:text-2xl tracking-wide text-[var(--warm-charcoal)] truncate mt-px">
              {content.header.brand}
            </h1>
          </div>
          
          <nav className="hidden md:flex items-center gap-8">
            <a href="#services" className="text-sm tracking-wide transition-colors hover:text-[var(--warm-caramel)]">{content.header.navServices}</a>
            <a href="#specialists" className="text-sm tracking-wide transition-colors hover:text-[var(--warm-caramel)]">{content.header.navTeam}</a>
            <a href="#contact" className="text-sm tracking-wide transition-colors hover:text-[var(--warm-caramel)]">{content.header.navContact}</a>
            
            <div className="flex bg-[var(--soft-beige)] rounded-full p-1 shadow-[inset_0_1px_3px_rgba(0,0,0,0.03)] ml-2 mr-2">
              <button 
                onClick={() => setLanguage('en')} 
                className={`px-3 sm:px-4 py-1.5 rounded-full text-[10px] font-medium tracking-widest uppercase transition-all duration-300 ${currentLang === 'en' ? 'bg-white text-[var(--warm-caramel)] shadow-sm' : 'text-[var(--dark-taupe)] hover:text-[var(--warm-charcoal)]'}`}
              >
                EN
              </button>
              <button 
                onClick={() => setLanguage('th')} 
                className={`px-3 sm:px-4 py-1.5 rounded-full text-[10px] font-medium tracking-widest uppercase transition-all duration-300 ${currentLang === 'th' ? 'bg-white text-[var(--warm-caramel)] shadow-sm' : 'text-[var(--dark-taupe)] hover:text-[var(--warm-charcoal)]'}`}
              >
                TH
              </button>
              <button 
                onClick={() => setLanguage('zh')} 
                className={`px-3 sm:px-4 py-1.5 rounded-full text-[10px] font-medium tracking-widest transition-all duration-300 ${currentLang === 'zh' ? 'bg-white text-[var(--warm-caramel)] shadow-sm' : 'text-[var(--dark-taupe)] hover:text-[var(--warm-charcoal)]'}`}
              >
                中文
              </button>
            </div>

            <button 
              onClick={handleBooking}
              className={`px-6 py-2.5 border rounded-full text-sm tracking-wide transition-all duration-300 font-medium flex items-center gap-2 ${bookingConfig.mode === 'line' ? 'bg-transparent text-[var(--warm-caramel)] border-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white' : 'bg-[var(--warm-caramel)] text-white border-transparent hover:bg-[var(--soft-bronze)]'}`}
            >
              {bookingConfig.mode === 'line' ? content.header.btnBookLine : content.header.btnBookWeb}
            </button>
          </nav>
          
          <div className="md:hidden flex items-center gap-1.5 sm:gap-3 flex-shrink-0 ml-2">
            <div className="relative flex items-center">
              <button 
                onClick={() => setLangPopoverOpen(!langPopoverOpen)}
                className="flex items-center justify-center gap-1 p-2 rounded-full text-[var(--dark-taupe)] hover:bg-[var(--soft-beige)] hover:text-[var(--warm-charcoal)] transition-colors focus:outline-none active:scale-95"
                aria-label="Select Language"
              >
                <svg className="w-[18px] h-[18px]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
                </svg>
                <span className="text-[10px] font-medium tracking-widest uppercase">{currentLang}</span>
              </button>

              {langPopoverOpen && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setLangPopoverOpen(false)} />
                  <div className="absolute right-0 top-full mt-3 w-36 bg-white rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.08)] border border-[var(--border)] border-opacity-30 p-2 z-50 origin-top-right transition-all">
                    <button 
                      onClick={() => { setLanguage('en'); setLangPopoverOpen(false); }}
                      className={`w-full text-left px-4 py-3 rounded-xl text-[14px] transition-all duration-200 ${currentLang === 'en' ? 'bg-[var(--soft-beige)] text-[var(--warm-caramel)] font-medium' : 'text-[var(--warm-charcoal)] hover:bg-[var(--soft-beige)]'}`}
                    >
                      English
                    </button>
                    <button 
                      onClick={() => { setLanguage('th'); setLangPopoverOpen(false); }}
                      className={`w-full text-left px-4 py-3 rounded-xl text-[14px] transition-all duration-200 ${currentLang === 'th' ? 'bg-[var(--soft-beige)] text-[var(--warm-caramel)] font-medium' : 'text-[var(--warm-charcoal)] hover:bg-[var(--soft-beige)]'}`}
                    >
                      ไทย
                    </button>
                    <button 
                      onClick={() => { setLanguage('zh'); setLangPopoverOpen(false); }}
                      className={`w-full text-left px-4 py-3 rounded-xl text-[14px] tracking-widest transition-all duration-200 ${currentLang === 'zh' ? 'bg-[var(--soft-beige)] text-[var(--warm-caramel)] font-medium' : 'text-[var(--warm-charcoal)] hover:bg-[var(--soft-beige)]'}`}
                    >
                      简体中文
                    </button>
                  </div>
                </>
              )}
            </div>
            
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)} 
              className="flex items-center gap-1.5 bg-[var(--soft-beige)]/50 hover:bg-[var(--soft-beige)] border border-[var(--border)]/30 rounded-full px-3 py-2 text-[var(--warm-charcoal)] transition-all focus:outline-none active:scale-95" 
              aria-label="Toggle menu"
            >
              <svg className="w-4 h-4 text-[var(--warm-caramel)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
                {mobileMenuOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                )}
              </svg>
              <span className="text-[10px] sm:text-[11px] font-medium tracking-wide uppercase">{mobileMenuOpen ? content.header.close : content.header.menu}</span>
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile Menu Expansion */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-[var(--border)] border-opacity-30 bg-[var(--warm-cream)] backdrop-blur-sm shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
          <nav className="px-5 sm:px-6 py-6 flex flex-col gap-1">
            <a href="#services" onClick={() => setMobileMenuOpen(false)} className="text-[15px] tracking-wide py-3 text-[#3d3530] hover:text-[var(--warm-caramel)] transition-colors font-medium">{content.header.navServices}</a>
            <a href="#specialists" onClick={() => setMobileMenuOpen(false)} className="text-[15px] tracking-wide py-3 text-[#3d3530] hover:text-[var(--warm-caramel)] transition-colors font-medium">{content.header.navTeam}</a>
            <a href="#contact" onClick={() => setMobileMenuOpen(false)} className="text-[15px] tracking-wide py-3 text-[#3d3530] hover:text-[var(--warm-caramel)] transition-colors font-medium">{content.header.navContact}</a>
            <button 
              onClick={() => { handleBooking(); setMobileMenuOpen(false); }}
              className={`mt-3 w-full px-6 py-4 border rounded-full text-sm tracking-wide flex items-center justify-center gap-2 transition-all duration-300 font-medium ${bookingConfig.mode === 'line' ? 'bg-transparent text-[var(--warm-caramel)] border-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white' : 'bg-[var(--warm-caramel)] text-white border-transparent hover:bg-[var(--soft-bronze)]'}`}
            >
              {bookingConfig.mode === 'line' ? content.header.btnBookLine : content.header.btnBookWeb}
            </button>
          </nav>
        </div>
      )}
    </header>
    {/* Spacer to compensate for fixed header removed from document flow */}
    <div className="h-16 md:h-20" />
    </>
  );
}
