// @ts-ignore
import shopConfig from '../../shop-config.json';

export const bookingConfig = {
  // Operation mode: toggle between 'line' and future 'web' backend integration
  mode: (shopConfig?.features?.booking?.enabled ? 'line' : 'disabled') as 'line' | 'web' | 'disabled',
  
  // Configured destination URL for LINE Official Account redirection
  lineUrl: shopConfig?.shop?.line_id 
    ? `https://line.me/R/ti/p/${shopConfig.shop.line_id.startsWith('@') ? shopConfig.shop.line_id : '@' + shopConfig.shop.line_id}`
    : 'https://line.me/R/ti/p/@serenity-massage',
  
  // Future placeholder for internal web-app booking route or system modal
  webRoute: '/booking',
};

/**
 * Universal Booking Handler
 * Decouples the UI component from the booking routing logic.
 */
export const handleBooking = () => {
  if (bookingConfig.mode === 'line') {
    // Execute secure external handoff instantly
    window.open(bookingConfig.lineUrl, '_blank', 'noopener,noreferrer');
  } else if (bookingConfig.mode === 'web') {
    // Prepared for Phase 2 internal routing or backend system trigger
    console.log('Routing to web booking engine:', bookingConfig.webRoute);
    window.location.href = bookingConfig.webRoute;
  }
};

