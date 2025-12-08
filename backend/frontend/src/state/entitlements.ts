// Centralized entitlement helpers for plan-based gating
// Future-proof: map features to plans to support plus/team, etc.

export type PlanId = 'free' | 'pro' | string;

export function isPro(planId: PlanId): boolean {
  return planId === 'pro';
}

export function canExportToYouTube(planId: PlanId): boolean {
  return isPro(planId);
}

export function canUseRegenerate(planId: PlanId): boolean {
  return isPro(planId);
}

export function canUseS3(planId: PlanId): boolean {
  return isPro(planId);
}

// Example future extension:
// const FEATURES: Record<string, PlanId[]> = {
//   youtube_export: ['pro'],
//   regenerate: ['pro'],
//   s3_urls: ['pro'],
// };