import React, { useState, useEffect } from 'react';
import { useLanguage } from '../hooks/useLanguage';
import { handleBooking } from '../config/booking';

type Status = 'available' | 'busy' | 'off';
type Tier = 'Normal' | 'VIP' | 'VVIP';

const LOCAL_DICT: Record<string, any> = {
  en: {
    avail: 'Available', busy: 'Busy', off: 'Off',
    availNow: 'Available now', offToday: 'Off today', availIn: 'Available in', min: 'min'
  },
  th: {
    avail: 'ว่าง', busy: 'ติดลูกค้า', off: 'หยุด',
    availNow: 'พร้อมให้บริการ', offToday: 'หยุดวันนี้', availIn: 'ว่างในอีก', min: 'นาที'
  },
  zh: {
    avail: '空闲', busy: '忙碌', off: '休息',
    availNow: '当前空闲', offToday: '今日休息', availIn: '预计', min: '分钟后空闲'
  }
};

const TIER_STYLES: Record<Tier, string> = {
  VVIP: 'bg-[#7A6554]/80 text-white/90',
  VIP:  'bg-[#B8956A]/80 text-white/90',
  Normal: 'bg-white/70 text-[var(--dark-taupe)]',
};

function TherapistCard({ member, content, dict }: { member: any, content: any, dict: any }) {
  const [status, setStatus] = useState<Status>('available');
  const [timeLeft, setTimeLeft] = useState(0);
  const [flipped, setFlipped] = useState(false);

  // Deterministic tier from member ID
  const tierHash = member.id.charCodeAt(0) + member.id.charCodeAt(member.id.length - 1);
  const tier: Tier = tierHash % 4 === 0 ? 'VVIP' : tierHash % 2 === 0 ? 'VIP' : 'Normal';

  useEffect(() => {
    const hash = member.id.charCodeAt(member.id.length - 1);
    let initialStatus: Status = 'available';
    let initialTime = 0;
    
    if (hash % 3 === 0) { initialStatus = 'off'; }
    else if (hash % 2 === 0) {
      initialStatus = 'busy';
      initialTime = Math.floor(Math.random() * 600) + 120;
    }
    
    setStatus(initialStatus);
    setTimeLeft(initialTime);
  }, [member.id]);

  useEffect(() => {
    if (status !== 'busy') return;
    
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          setStatus('available');
          const availDuration = Math.floor(Math.random() * 10) + 5;
          setTimeout(() => {
            setStatus('busy');
            setTimeLeft(Math.floor(Math.random() * 1200) + 600);
          }, availDuration * 1000);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    
    return () => clearInterval(timer);
  }, [status]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleFlip = () => setFlipped((f) => !f);

  return (
    <div className="bg-white rounded-[2rem] overflow-hidden shadow-sm hover:shadow-[var(--shadow-premium)] transition-all duration-500 group flex flex-col border border-[var(--border)] border-opacity-20">
      
      {/* Image Container with Flip */}
      <div 
        className="relative aspect-[4/5] cursor-pointer group/flip" 
        style={{ perspective: '1000px' }}
        onClick={handleFlip}
      >
        <div 
          className="relative w-full h-full transition-transform duration-700 ease-in-out group-hover/flip:scale-[1.02] group-active/flip:scale-[0.98]"
          style={{ 
            transformStyle: 'preserve-3d',
            transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)'
          }}
        >
          {/* Front */}
          <div className="absolute inset-0 bg-[var(--soft-beige)] overflow-hidden" style={{ backfaceVisibility: 'hidden' }}>
            <img 
              src={member.image} 
              alt={member.name}
              className="w-full h-full object-cover object-top sm:object-center group-hover:scale-[1.03] transition-transform duration-700 ease-in-out"
            />
          </div>

          {/* Back */}
          <div 
            className="absolute inset-0 bg-[var(--soft-beige)] overflow-hidden flex items-center justify-center" 
            style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
          >
            <img 
              src={member.imageAlt || member.image} 
              alt={`${member.name} lifestyle`}
              className="w-full h-full object-cover object-center"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[var(--deep-cocoa)]/30 to-transparent" />
          </div>
        </div>

        {/* Availability Badge — top-left, always visible */}
        <div className={`absolute top-3 left-3 sm:top-4 sm:left-4 px-2.5 py-1 rounded-lg text-[9px] sm:text-[10px] font-medium tracking-widest uppercase backdrop-blur-md shadow-sm border border-white/20 transition-colors z-10 ${
          status === 'available' ? 'bg-[#EEF4EF]/90 text-[#3D5A40]' :
          status === 'busy' ? 'bg-[var(--warm-cream)]/95 text-[var(--warm-caramel)]' :
          'bg-[#F5F5F5]/90 text-[#8E8E8E]'
        }`}>
          {status === 'available' ? dict.avail : status === 'off' ? dict.off : formatTime(timeLeft)}
        </div>

        {/* Tier Badge — bottom-left, secondary weight */}
        <div className={`absolute bottom-3 left-3 sm:bottom-4 sm:left-4 px-2 py-0.5 rounded text-[8px] font-medium tracking-[0.1em] uppercase backdrop-blur-sm shadow-sm border border-white/10 z-10 opacity-80 ${TIER_STYLES[tier]}`}>
          {tier}
        </div>

        {/* Flip hint icon — subtle, fades after first flip */}
        {!flipped && (
          <div className="absolute bottom-3 right-3 sm:bottom-4 sm:right-4 z-10 opacity-0 group-hover/flip:opacity-40 transition-opacity duration-500 pointer-events-none">
            <svg className="w-4 h-4 text-white drop-shadow" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 00-3.7-3.7 48.678 48.678 0 00-7.324 0 4.006 4.006 0 00-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3l-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 003.7 3.7 48.656 48.656 0 007.324 0 4.006 4.006 0 003.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3l-3 3" />
            </svg>
          </div>
        )}
      </div>

      {/* Data Container */}
      <div className="px-5 pt-5 pb-6 sm:px-7 sm:pt-6 sm:pb-8 flex flex-col flex-grow items-center text-center">
        
        {/* Name & Role */}
        <div className="space-y-1">
          <h3 className="text-base sm:text-lg md:text-[22px] font-medium tracking-tight text-[var(--warm-charcoal)] group-hover:text-[var(--warm-caramel)] transition-colors leading-snug">{member.name}</h3>
          <p className="text-[11px] sm:text-[13px] text-[var(--dark-taupe)] opacity-80">{member.role}</p>
        </div>

        {/* Secondary Status Line */}
        <div className="mt-3 sm:mt-4 flex items-center justify-center gap-2 text-[11px] sm:text-[13px] font-medium min-h-[20px]">
          {status === 'available' && (
            <><span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[#5E8B62] animate-[pulse_2s_cubic-bezier(0.4,0,0.6,1)_infinite]"></span><span className="text-[#5E8B62]">{dict.availNow}</span></>
          )}
          {status === 'busy' && (
            <><span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[var(--warm-caramel)] opacity-70"></span><span className="text-[var(--warm-caramel)]">{dict.availIn} {Math.ceil(timeLeft / 60)} {dict.min}</span></>
          )}
          {status === 'off' && (
            <><span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-[#A8A8A8]"></span><span className="text-[#8E8E8E]">{dict.offToday}</span></>
          )}
        </div>
        
        {/* CTA Button */}
        <div className="mt-auto pt-5 sm:pt-6 w-full">
          <button 
            onClick={handleBooking}
            className="w-full px-4 py-3 sm:py-3.5 sm:px-6 border border-[var(--warm-caramel)] rounded-full text-xs sm:text-[13px] tracking-wide text-[var(--warm-caramel)] hover:bg-[#06C755] hover:border-[#06C755] hover:text-white transition-all font-medium active:scale-[0.98]"
          >
            {content.team.ctaButton}
          </button>
        </div>

      </div>
    </div>
  );
}

export function TeamSection() { 
  const { content, currentLang } = useLanguage() as any;
  const dict = LOCAL_DICT[currentLang] || LOCAL_DICT['en'];

  return (
    <section id="specialists" className="py-16 sm:py-20 lg:py-28 bg-[var(--warm-cream)]">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 lg:px-8">
        <div className="text-center mb-10 sm:mb-14 lg:mb-16 space-y-4">
          <h2 className="text-3xl lg:text-4xl tracking-tight text-[var(--warm-charcoal)] font-normal">{content.team.title}</h2>
          <p className="text-base sm:text-lg text-[var(--dark-taupe)] max-w-2xl mx-auto leading-relaxed">{content.team.description}</p>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-7 lg:gap-10">
          {content.team.items.map((member: any) => (
            <TherapistCard key={member.id} member={member} content={content} dict={dict} />
          ))}
        </div>
      </div>
    </section>
  ); 
}
