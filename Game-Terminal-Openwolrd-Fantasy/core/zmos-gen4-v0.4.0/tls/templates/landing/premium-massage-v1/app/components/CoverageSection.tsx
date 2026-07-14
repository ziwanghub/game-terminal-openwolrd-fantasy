import React, { useState } from 'react';
import { useLanguage } from '../hooks/useLanguage';

export function CoverageSection() { 
  const { content } = useLanguage() as any;
  const [distanceInput, setDistanceInput] = useState<number | ''>('');

  const configRatePerKm = 20;
  
  let resultDisplay = '฿0';
  let isLongDistance = false;
  let isFreeResult = false;

  if (distanceInput !== '') {
    const dist = Number(distanceInput);
    if (dist <= 10) {
      resultDisplay = content.coverage.free || 'Free';
      isFreeResult = true;
    } else if (dist <= 13) {
      resultDisplay = '฿450';
    } else if (dist <= 15) {
      resultDisplay = '฿550';
    } else if (dist <= 20) {
      resultDisplay = '฿650';
    } else {
      resultDisplay = `฿${650 + ((dist - 20) * configRatePerKm)}`;
      isLongDistance = true;
    }
  }

  return (
    <section id="areas" className="py-20 lg:py-32 bg-[var(--soft-beige)] transition-colors duration-700">
      <div className="max-w-5xl mx-auto px-5 sm:px-6 lg:px-8">
        
        {/* Global Section Header */}
        <div className="space-y-5 text-center mb-12 w-full">
          <div className="flex items-center justify-center gap-3">
            <h2 className="text-3xl lg:text-[40px] text-[var(--warm-charcoal)] font-light tracking-tight">
              {content.coverage.title}
            </h2>
            <div className="relative group flex items-center justify-center w-5 h-5 rounded-full border border-[var(--warm-caramel)] border-opacity-40 text-[var(--warm-caramel)] text-xs cursor-help transition-all duration-300 hover:border-opacity-100 hover:bg-[var(--warm-cream)]">
              ?
              <div className="absolute bottom-full mb-3 w-56 sm:w-64 right-1/2 translate-x-1/2 sm:right-auto sm:translate-x-0 bg-white p-4 rounded-2xl shadow-[var(--shadow-premium)] border border-[var(--border)] border-opacity-10 text-xs text-[var(--dark-taupe)] opacity-0 group-hover:opacity-100 transition-all duration-300 pointer-events-none z-50 text-center font-normal leading-relaxed translate-y-2 group-hover:translate-y-0">
                {content.coverage.tooltip}
              </div>
            </div>
          </div>
          <p className="text-lg text-[var(--dark-taupe)] leading-relaxed max-w-xl mx-auto opacity-80 font-light">
            {content.coverage.subtitle}
          </p>
        </div>

        {/* Unified Premium Card composition */}
        <div className="bg-white rounded-[2.5rem] shadow-[var(--shadow-premium)] border border-[var(--border)] border-opacity-20 overflow-hidden transition-all duration-500 hover:shadow-2xl">
          <div className="flex flex-col lg:flex-row items-stretch">

            {/* Right: Primary Calculator Hero (55% visual scale - Order 1 on mobile, 2 on desktop) */}
            <div className="w-full lg:w-[55%] p-8 sm:p-12 xl:p-14 order-1 lg:order-2 flex flex-col justify-center bg-white z-10">
              <div className="space-y-8 lg:space-y-10">
                
                <div className="space-y-2 text-center lg:text-left">
                  <h3 className="text-[var(--warm-charcoal)] font-normal text-2xl sm:text-3xl tracking-tight">{content.coverage.calcTitle}</h3>
                  <p className="text-[var(--dark-taupe)] text-sm opacity-80">{content.coverage.calcDesc}</p>
                </div>
                
                <div className="space-y-3 group">
                  <label className="text-[10px] font-semibold text-[var(--warm-caramel)] uppercase tracking-[0.2em] ml-2 opacity-80 transition-opacity group-focus-within:opacity-100">{content.coverage.calcDistanceLabel}</label>
                  <input 
                    type="number" 
                    min="0"
                    value={distanceInput}
                    onChange={(e) => setDistanceInput(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full bg-[var(--soft-beige)] bg-opacity-10 border border-[var(--border)] border-opacity-20 rounded-2xl px-6 py-5 sm:py-6 text-[var(--warm-charcoal)] text-3xl font-light outline-none focus:bg-white focus:border-[var(--warm-caramel)] focus:border-opacity-40 focus:ring-4 focus:ring-[var(--warm-caramel)] focus:ring-opacity-10 transition-all shadow-[inset_0_2px_10px_rgba(0,0,0,0.02)] text-center lg:text-left placeholder-opacity-30"
                    placeholder="e.g. 15"
                  />
                </div>

                <div className="space-y-3 pt-2">
                  <div className="bg-gradient-to-r from-[var(--warm-cream)] to-[var(--soft-beige)] bg-opacity-20 rounded-2xl py-8 px-6 sm:px-10 flex flex-col sm:flex-row justify-between items-center border border-[var(--warm-caramel)] border-opacity-10 shadow-sm gap-3 sm:gap-0 transition-all duration-500 hover:shadow-md">
                    <span className="text-[var(--dark-taupe)] font-medium tracking-[0.1em] uppercase text-xs opacity-70">{content.coverage.calcResultLabel}</span>
                    <span className={`text-[32px] sm:text-[40px] md:text-[46px] leading-none tracking-tight transition-colors duration-500 ease-in-out ${isFreeResult ? 'text-[var(--warm-caramel)] font-medium' : 'text-[var(--warm-charcoal)] font-light'}`}>
                      {distanceInput !== '' ? resultDisplay : '฿0'}
                    </span>
                  </div>
                  
                  <div className={`transition-all duration-500 ease-in-out overflow-hidden ${isLongDistance ? 'opacity-100 max-h-10 mt-3' : 'opacity-0 max-h-0 mt-0'}`}>
                    <p className="text-center sm:text-right text-[11px] text-[var(--warm-caramel)] font-medium tracking-wide px-2 opacity-80">
                      {content.coverage.calcLongDistance || 'Includes long-distance surcharge'}
                    </p>
                  </div>
                </div>

                <p className="text-[11px] text-[var(--dark-taupe)] opacity-50 italic leading-relaxed pt-2 text-center lg:text-left">
                  * {content.coverage.calcHelper}
                </p>
                
              </div>
            </div>

            {/* Left: Secondary Pricing Guide (45% visual scale - Order 2 on mobile, 1 on desktop) */}
            <div className="w-full lg:w-[45%] p-8 sm:p-12 xl:p-14 bg-gradient-to-b lg:bg-gradient-to-r from-[var(--soft-beige)]/10 to-[var(--soft-beige)]/30 order-2 lg:order-1 flex flex-col justify-center border-t lg:border-t-0 lg:border-r border-[var(--border)] border-opacity-10 relative">
              
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-px h-2/3 bg-gradient-to-b from-transparent via-[var(--border)] to-transparent opacity-20 hidden lg:block"></div>

              <h4 className="text-[var(--dark-taupe)] font-semibold text-[10px] tracking-[0.25em] uppercase mb-10 text-center lg:text-left opacity-60">
                {content.coverage.guideTitle || 'Pricing Guide'}
              </h4>
              
              <div className="space-y-1 w-full max-w-[280px] mx-auto lg:mx-0">
                {content.coverage.tiers.map((tier: any, idx: number) => {
                  const isFree = idx === 0;
                  return (
                    <div key={idx} className={`flex justify-between items-center py-4 border-b border-[var(--border)] border-opacity-10 last:border-0 hover:bg-white hover:bg-opacity-40 hover:shadow-sm px-3 -mx-3 rounded-xl transition-all duration-300 ${isFree ? 'opacity-100 bg-white bg-opacity-30' : 'opacity-80'}`}>
                      <span className={`text-[15px] font-medium tracking-wide ${isFree ? 'text-[var(--warm-caramel)]' : 'text-[var(--dark-taupe)]'}`}>{tier.distance}</span>
                      <span className={`text-[15px] tracking-wide ${isFree ? 'text-[var(--warm-caramel)] font-semibold' : 'text-[var(--warm-charcoal)] font-medium'}`}>{tier.price}</span>
                    </div>
                  );
                })}
              </div>

            </div>

          </div>
        </div>

      </div>
    </section>
  ); 
}
