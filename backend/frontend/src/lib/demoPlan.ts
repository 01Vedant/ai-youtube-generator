export const demoPlan = {
  topic: 'Welcome to BhaktiGen',
  language: 'hi-IN',
  voice_id: 'hi-IN-SwaraNeural',
  template: 'parallax_basic',
  fast_path: true,
  scenes: [
    { image_prompt: 'sunrise over temple gopuram, soft light, devotional art, high detail', duration_sec: 6 },
    { image_prompt: 'hands folded in prayer, warm glow, serene background', duration_sec: 5 },
  ],
} as const;