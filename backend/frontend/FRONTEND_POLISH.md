# Frontend Polish: Retry Logic, Error Handling & Toast System

## Summary of Changes

This update enhances the integrated frontend-backend flow with production-grade resilience, user feedback, and error recovery.

### 1. **API Layer Enhancements** (`src/lib/api.ts`)

#### Exponential Backoff Retry
- **`postRender(plan, attemptNumber)`**: Retries on 429/5xx with exponential backoff (1s → 5s) up to 3 attempts
- **`getStatus(jobId, attemptNumber, lastGoodState)`**: Retries transient errors up to 5 times, stops on terminal states
- **Smart fallback**: Returns last good state on transient errors to prevent UI flickering
- **Backoff with jitter**: ±10% jitter to avoid thundering herd problems

#### Console Logging for Support
- Every API call logs with timestamp, jobId, attempt number, and event details
- Format: `[ISO-8601] [BhaktiGen] [Job: xxx-xxx] Event description { context }`
- Helps support team debug issues without intrusive UI alerts

#### Terminal State Detection
- Stops polling immediately on `success`, `error`, or `failed` states
- Reduces unnecessary API calls and server load

### 2. **Toast System** (`src/lib/toast.ts` + `src/components/Toast.tsx`)

#### Toast Manager
- Centralized toast event emitter with pub-sub pattern
- No React Context needed; subscribers always up-to-date
- Auto-dismiss on configurable duration (0 = manual dismiss)
- Support for toast links (e.g., "View Video" with href)

#### Toast Component
- Sticky bottom-right positioning (fixed, z-index 9999)
- Four toast types: `success`, `warning`, `error`, `info`
- Smooth slide-in/out animations
- Dismiss button + auto-dismiss timer
- Mobile-responsive (adapts to narrow screens)

#### Toast Usage
```typescript
import { toast } from "../lib/toast";

toast.success("Video ready!");
toast.warning("YouTube upload skipped", 5000);
toast.error("Failed to generate audio");
toast.info("Processing image 2/5");
```

### 3. **CreateVideoPage Enhancement** (`src/pages/CreateVideoPage.tsx`)

- Import `toast` utility
- Show success toast on job creation with job ID
- Show error toast on validation/API failure
- Error message still displayed in form for inline feedback
- All retry logic handled transparently by `postRender()`

### 4. **RenderStatusPage Enhancement** (`src/pages/RenderStatusPage.tsx`)

#### Inline Error Banner
- Displays transient errors without removing status UI
- Shows "Retrying automatically..." hint
- Manual "Retry" button for explicit refresh
- Animated slide-down entrance
- Keeps last known state visible during network blips

#### Smart Toast Notifications
- Success toast on job completion (different message if YouTube uploaded)
- Warning toast if YouTube upload skipped (partial failure)
- Error toast only on terminal job failure
- Avoids toast spam on duplicate errors

#### Defensive Null Checks
- `status.assets`: Only render if exists and has entries
- `status.logs`: Handle empty/null arrays gracefully
- All string conversions with fallback to "—"
- UI never crashes even if API returns malformed data

#### Retry Logic Integration
- Tracks `isRetrying` state for button feedback
- Passes `lastGoodState` to `getStatus()` for recovery
- Auto-refresh toggle unaffected by transient errors
- Manual retry button for user-initiated refresh

### 5. **App Integration** (`src/App.jsx`)

- Add `<ToastContainer />` to render toast notifications globally
- Toasts appear bottom-right, above all other UI elements
- Single instance; all pages can show toasts

### 6. **CSS Enhancements** (`RenderStatusPage.css`)

#### Error Banner Styling
- Red border + light red background (`#ffe6e6` / `#ff6b6b`)
- Icon + message + hint text
- Retry button with hover effect and animation
- Responsive layout (flex for desktop, stacks on mobile)

#### Toast Container Styling (`Toast.css`)
- Position: bottom-right corner (fixed, z-index 9999)
- Slide-in animation (300ms) + slide-out on dismiss
- Four color variants (green/amber/red/blue)
- Left border indicator (4px solid)
- Max-width 400px; adapts to mobile

## Key Features

### Resilience
✓ Exponential backoff retry (1s → 5s) with jitter  
✓ Terminal state detection (stop polling on success/error)  
✓ Graceful error recovery (last good state fallback)  
✓ Defensive null checks (never crash UI)

### User Experience
✓ Toast notifications for key events (success, warning, error)  
✓ Inline error banner with "Retry" button  
✓ Job ID always visible for support reference  
✓ Auto-refresh toggle preserved even on transient errors  
✓ Logs display doesn't break on malformed data

### Support & Debugging
✓ Console logs with jobId for every API call  
✓ Retry attempt tracking  
✓ Timestamp on all logs  
✓ Clear, structured log format for easy parsing

### Frontend Files Modified/Added

**Modified:**
- `src/lib/api.ts` — Retry logic, backoff, logging
- `src/pages/CreateVideoPage.tsx` — Toast integration
- `src/pages/RenderStatusPage.tsx` — Error banner, retry button, defensive null checks
- `src/pages/RenderStatusPage.css` — Error banner + retry button styles
- `src/App.jsx` — ToastContainer integration

**New:**
- `src/lib/toast.ts` — Toast manager (pub-sub)
- `src/components/Toast.tsx` — Toast component + container
- `src/components/Toast.css` — Toast styling

## Testing Checklist

- [ ] Create job → success toast appears
- [ ] Network error during job creation → error toast + retry
- [ ] Job runs → status page polls every 2s
- [ ] Transient network error → error banner appears, keeps last state
- [ ] Manual retry → refreshes status
- [ ] Auto-refresh toggle works during transient errors
- [ ] Job completes → success toast + "View on YouTube" link (if available)
- [ ] YouTube upload skipped → warning toast
- [ ] Job fails → error toast + error banner
- [ ] Assets/logs missing → UI doesn't crash, shows "—"
- [ ] Console logs appear with jobId for every call
- [ ] Toast stacks bottom-right on desktop, mobile-responsive
