import type { RenderPlan } from '@/types/api';

export type Preset = {
  id: string;
  name: string;
  template: string;
  voice_id: 'hi-IN-SwaraNeural' | 'hi-IN-DiyaNeural';
  language: 'hi-IN';
  fast_path: boolean;
  scenes: { image_prompt: string; duration_sec: number }[];
};

export const presets: Preset[] = [
  {
    id: 'bhakti-parallax-soft',
    name: 'Bhakti Parallax – Soft',
    template: 'parallax_basic',
    voice_id: 'hi-IN-SwaraNeural',
    language: 'hi-IN',
    fast_path: false,
    scenes: [
      { image_prompt: 'soft devotional parallax, warm morning light', duration_sec: 6 },
      { image_prompt: 'temple interior, gentle parallax, incense', duration_sec: 5 },
    ],
  },
  {
    id: 'aarti-focus-warm',
    name: 'Aarti Focus – Warm',
    template: 'aarti_warm',
    voice_id: 'hi-IN-DiyaNeural',
    language: 'hi-IN',
    fast_path: false,
    scenes: [
      { image_prompt: 'aarti diya flame close-up, warm glow', duration_sec: 7 },
      { image_prompt: 'devotee hands offering, soft bokeh', duration_sec: 6 },
    ],
  },
  {
    id: 'temple-dawn-minimal',
    name: 'Temple Dawn – Minimal',
    template: 'minimal',
    voice_id: 'hi-IN-SwaraNeural',
    language: 'hi-IN',
    fast_path: true,
    scenes: [
      { image_prompt: 'temple silhouette at dawn, minimal composition', duration_sec: 8 },
    ],
  },
];

export function presetToPlan(p: Preset, title: string): RenderPlan {
  const scenes = p.scenes.map((s) => ({ image_prompt: s.image_prompt, narration: '', duration_sec: s.duration_sec }));
  return {
    topic: title,
    language: 'hi',
    voice: 'F',
    voice_id: p.voice_id,
    length: scenes.reduce((acc, cur) => acc + cur.duration_sec, 0),
    style: p.template,
    scenes,
    enable_parallax: p.template.includes('parallax'),
    enable_templates: true,
    enable_audio_sync: true,
    quality: 'final',
    fast_path: p.fast_path,
  } as RenderPlan;
}
