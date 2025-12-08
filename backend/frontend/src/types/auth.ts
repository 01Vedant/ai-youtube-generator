export type AuthTokens = { access_token: string; refresh_token: string; token_type: 'bearer' };
export type Entitlements = { features: string[]; quotas: Record<string, number> };
export type Me = {
    roles: any; id: string; email: string; created_at: string; plan_id: string; entitlements: Entitlements 
};
