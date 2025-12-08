/**
 * BillingPage: Show subscription status, upgrade button, plan details
 */

import React, { useEffect, useState } from 'react';
import './BillingPage.css';
import { toast } from '../lib/toast';
import { getBillingSubscription, createCheckoutSession, createPortalSession, getMe } from '../lib/api';
import { useAuth } from '@/state/auth';

interface SubscriptionInfo {
  plan: string;
  status: string;
  current_period_end: string | null;
  customer_id: string | null;
}

export const BillingPage: React.FC = () => {
  const { user } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSubscription = async (): Promise<void> => {
      try {
        const data = (await getBillingSubscription()) as SubscriptionInfo;
        setSubscription(data);
      } catch (err) {
        console.error('Failed to fetch subscription:', err);
        toast.error('Failed to load billing info');
      } finally {
        setLoading(false);
      }
    };

    fetchSubscription();
    // Handle return from Stripe success/cancel
    const qs = new URLSearchParams(window.location.search);
    if (qs.has('session_id')) {
      getMe()
        .then(() => {
          toast.success('Plan updated to Pro');
          // Refresh subscription UI to reflect new plan
          getBillingSubscription()
            .then((data) => setSubscription(data as SubscriptionInfo))
            .catch(() => {});
        })
        .catch(() => {});
    } else if (window.location.pathname.endsWith('/billing/cancel')) {
      toast.info('Checkout canceled');
    }
  }, []);

  const handleUpgrade = async (plan: string): Promise<void> => {
    try {
      const data = (await createCheckoutSession(plan)) as { checkout_url?: string; url?: string };
      const checkoutUrl = data.checkout_url || data.url;
      if (checkoutUrl) {
        window.location.href = checkoutUrl;
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      toast.error(message);
    }
  };

  if (loading) {
    return <div className="billing-page loading">Loading...</div>;
  }

  return (
    <div className="billing-page">
      <div className="container">
        <h1>💳 Billing & Plans</h1>
        <div style={{ marginBottom: 12 }}>
          {user?.plan_id === 'pro' ? (
            <button
              className="btn btn-secondary"
              onClick={async () => {
                try {
                  const { url } = await createPortalSession();
                  if (url) window.location.href = url;
                } catch (e) {
                  toast.error('Unable to open billing portal');
                }
              }}
            >
              Manage Billing
            </button>
          ) : (
            <button className="btn btn-primary" onClick={() => handleUpgrade('pro')}>Go Pro</button>
          )}
        </div>

        <div className="current-plan">
          <h2>Current Plan</h2>
          {subscription && (
            <div className="plan-status">
              <div className="plan-name">{subscription.plan.toUpperCase()}</div>
              <div className="plan-status-badge">{subscription.status}</div>
              {subscription.current_period_end && (
                <div className="plan-period">
                  Renews on {new Date(subscription.current_period_end).toLocaleDateString()}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="plans-grid">
          {/* Free Plan */}
          <div className={`plan-card ${subscription?.plan === 'free' ? 'active' : ''}`}>
            <div className="plan-header">
              <h3>Free</h3>
              <div className="price">$0/month</div>
            </div>
            <ul className="plan-features">
              <li>✓ 500 images/month</li>
              <li>✓ 1,000 min TTS/month</li>
              <li>✓ 100 render minutes/month</li>
              <li>✓ 100 GB storage</li>
              <li>✓ Community support</li>
            </ul>
            {subscription?.plan === 'free' && (
              <button className="btn btn-secondary btn-full" disabled>
                Current Plan
              </button>
            )}
          </div>

          {/* Pro Plan */}
          <div className={`plan-card featured ${subscription?.plan === 'pro' ? 'active' : ''}`}>
            <div className="plan-badge">Popular</div>
            <div className="plan-header">
              <h3>Pro</h3>
              <div className="price">$29/month</div>
            </div>
            <ul className="plan-features">
              <li>✓ 2,500 images/month</li>
              <li>✓ 5,000 min TTS/month</li>
              <li>✓ 500 render minutes/month</li>
              <li>✓ 500 GB storage</li>
              <li>✓ 4K rendering</li>
              <li>✓ YouTube publishing</li>
              <li>✓ Priority support</li>
            </ul>
            {subscription?.plan === 'pro' ? (
              <button className="btn btn-secondary btn-full" disabled>
                Current Plan
              </button>
            ) : (
              <button
                className="btn btn-primary btn-full"
                onClick={() => handleUpgrade('pro')}
              >
                Upgrade to Pro
              </button>
            )}
          </div>

          {/* Enterprise Plan */}
          <div className={`plan-card ${subscription?.plan === 'enterprise' ? 'active' : ''}`}>
            <div className="plan-header">
              <h3>Enterprise</h3>
              <div className="price">Custom</div>
            </div>
            <ul className="plan-features">
              <li>✓ Unlimited everything</li>
              <li>✓ Dedicated support</li>
              <li>✓ Custom integrations</li>
              <li>✓ SLA guarantee</li>
              <li>✓ Advanced analytics</li>
            </ul>
            <button
              className="btn btn-secondary btn-full"
              onClick={() => (window.location.href = 'mailto:sales@example.com')}
            >
              Contact Sales
            </button>
          </div>
        </div>

        <div className="billing-info">
          <h3>💡 Billing Details</h3>
          <ul>
            <li>All plans include 30-day free trial. No credit card required.</li>
            <li>Pricing is per-project, not per-user. Teams on same account share quota.</li>
            <li>
              Overage charges: Images $0.05 each, TTS $0.001/sec, Render $0.10/min, Storage $0.10/GB/month.
            </li>
            <li>Cancel anytime. No long-term contracts.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
