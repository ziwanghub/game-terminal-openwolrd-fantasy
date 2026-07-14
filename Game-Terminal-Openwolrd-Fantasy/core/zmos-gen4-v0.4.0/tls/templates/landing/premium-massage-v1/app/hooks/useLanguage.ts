import { useState, useEffect } from 'react';
import { en } from '../content/en';
import { th } from '../content/th';
import { zh } from '../content/zh';

// Injected by TLS engine at runtime
// @ts-ignore
import shopConfig from '../../shop-config.json';

export type LanguageType = 'en' | 'th' | 'zh';

const contentMap = { en, th, zh };

function deepMerge(target: any, source: any) {
  const isObject = (obj: any) => obj && typeof obj === 'object' && !Array.isArray(obj);
  
  let output = Object.assign({}, target);
  if (isObject(target) && isObject(source)) {
    Object.keys(source).forEach(key => {
      if (isObject(source[key])) {
        if (!(key in target)) {
          Object.assign(output, { [key]: source[key] });
        } else {
          output[key] = deepMerge(target[key], source[key]);
        }
      } else {
        Object.assign(output, { [key]: source[key] });
      }
    });
  }
  return output;
}

/**
 * Maps shop-config.json fields to the content object structure
 */
function mapConfigToContent(content: any, config: any) {
  if (!config) return content;

  const overrides: any = {};
  
  if (config.shop) {
    overrides.header = { brand: config.shop.name };
    overrides.hero = { tag: config.shop.tagline, description: config.shop.tagline };
    overrides.footer = { brand: config.shop.name.toUpperCase() };
  }

  if (config.services) {
    overrides.services = {
      items: config.services.map((s: any) => ({
        id: s.id,
        title: s.name,
        desc: s.description,
        image: s.image,
        tag: s.tag,
        options: s.options
      }))
    };
  }

  if (config.staff) {
    overrides.team = {
      items: config.staff.map((s: any) => ({
        id: s.id,
        name: s.name,
        role: s.role,
        tag: s.tag,
        image: s.photo,
        imageAlt: s.photo
      }))
    };
  }

  return deepMerge(content, overrides);
}

export function useLanguage() {
  const [currentLang, setCurrentLangState] = useState<LanguageType>('en');

  useEffect(() => {
    const saved = localStorage.getItem('serenity_lang') as LanguageType;
    if (saved && contentMap[saved]) {
      setCurrentLangState(saved);
    }

    const handleLangChange = () => {
      const active = localStorage.getItem('serenity_lang') as LanguageType;
      if (active && contentMap[active]) {
        setCurrentLangState(active);
      }
    };
    
    window.addEventListener('serenityLangUpdate', handleLangChange);
    return () => window.removeEventListener('serenityLangUpdate', handleLangChange);
  }, []);

  const setLanguage = (lang: LanguageType) => {
    localStorage.setItem('serenity_lang', lang);
    setCurrentLangState(lang);
    window.dispatchEvent(new Event('serenityLangUpdate'));
  };

  const baseContent = currentLang === 'en' ? en : deepMerge(en, contentMap[currentLang]);

  return {
    content: mapConfigToContent(baseContent, shopConfig),
    currentLang,
    setLanguage,
    config: shopConfig
  };
}

