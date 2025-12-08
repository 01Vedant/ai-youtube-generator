/// <reference types="vite/client" />

declare global {
  interface Window {
    __SHOW_ONBOARDING_MODAL?: () => void;
    __ONBOARDING_STATE?: any;
    __track?: (event: string, meta?: any) => void;
  }
}

declare module "*.svg" { const src: string; export default src; }
declare module "*.png" { const src: string; export default src; }
declare module "*.jpg" { const src: string; export default src; }
declare module "*.mp3" { const src: string; export default src; }
