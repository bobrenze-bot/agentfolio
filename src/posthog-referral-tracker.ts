/**
 * AgentFolio PostHog Referral Tracker v2.0 (TypeScript)
 * Tracks referral sources and persists them as user properties
 */

interface Config {
  POSTHOG_API_KEY: string;
  POSTHOG_HOST: string;
  DEBUG: boolean;
}

interface StorageKeys {
  FIRST_TOUCH: string;
  SESSION_REFERRER: string;
  ATTRIBUTION_SYNCED: string;
}

type ReferrerType = 'direct' | 'social' | 'search' | 'developer' | 'referral' | 'unknown';

interface ReferrerData {
  type: ReferrerType;
  domain: string | null;
  full: string | null;
}

interface AttributionData {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  ref_param?: string;
  referrer_type: ReferrerType;
  referrer_domain?: string;
  referrer_url?: string;
  landing_path: string;
  landing_url: string;
  first_seen_at: string;
}

type UserProperties = Record<string, string | null | undefined> & {
  acquisition_source: string;
  acquisition_medium?: string;
  acquisition_campaign?: string;
  acquisition_referrer?: string;
  first_touch_type: string;
  first_touch_path: string;
  first_touch_timestamp: string;
  session_referrer_type?: string;
  session_referrer_domain?: string;
  session_landing_page?: string;
  agentfolio_page: 'profile' | 'listing';
  agent_handle?: string;
};

interface AnalyticsEventProperties {
  [key: string]: string | number | boolean | null | undefined;
}

interface AgentFolioAnalyticsAPI {
  trackEvent: (eventName: string, properties?: AnalyticsEventProperties) => void;
  trackPlatformClick: (platform: string, url: string) => void;
  trackShare: (shareMethod: string) => void;
  getAttribution: () => AttributionData;
}

declare global {
  interface Window {
    posthog: PostHog | undefined;
    AgentFolioAnalytics: AgentFolioAnalyticsAPI;
  }
}

interface PostHog {
  init: (apiKey: string, config: PostHogConfig) => void;
  capture: (eventName: string, properties?: AnalyticsEventProperties) => void;
  people: { set: (properties: Record<string, unknown>) => void };
  register: (properties: Record<string, unknown>) => void;
}

interface PostHogConfig {
  api_host: string;
  loaded?: () => void;
}

const CONFIG: Config = {
  POSTHOG_API_KEY: 'phc_YOUR_PROJECT_API_KEY_HERE',
  POSTHOG_HOST: 'https://us.i.posthog.com',
  DEBUG: false,
};

const STORAGE_KEYS: StorageKeys = {
  FIRST_TOUCH: 'af_first_touch',
  SESSION_REFERRER: 'af_session_referrer',
  ATTRIBUTION_SYNCED: 'af_attribution_synced',
};

const SOCIAL_DOMAINS = [
  'twitter.com', 'x.com', 'facebook.com', 'fb.com', 'linkedin.com',
  'reddit.com', 'bluesky.io', 'mastodon.social', 'instagram.com',
];

const SEARCH_DOMAINS = [
  'google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com',
  'ecosia.org', 'kagi.com', 'yandex.com', 'baidu.com',
];

const DEV_DOMAINS = [
  'github.com', 'producthunt.com', 'hackernews.ycombinator.com',
  'news.ycombinator.com', 'dev.to', 'medium.com',
];

function log(...args: unknown[]): void {
  if (CONFIG.DEBUG) console.log('[AF Referral]', ...args);
}

function getUrlParam(param: string): string | null {
  return new URLSearchParams(window.location.search).get(param);
}

function parseReferrer(referrer: string | null): ReferrerData {
  if (!referrer || referrer === 'null' || referrer === '') {
    return { type: 'direct', domain: null, full: null };
  }
  try {
    const url = new URL(referrer);
    const domain = url.hostname.toLowerCase().replace(/^www./, '');
    if (SOCIAL_DOMAINS.some(s => domain.includes(s))) {
      return { type: 'social', domain, full: referrer };
    }
    if (SEARCH_DOMAINS.some(s => domain.includes(s))) {
      return { type: 'search', domain, full: referrer };
    }
    if (DEV_DOMAINS.some(d => domain.includes(d))) {
      return { type: 'developer', domain, full: referrer };
    }
    return { type: 'referral', domain, full: referrer };
  } catch {
    return { type: 'unknown', domain: null, full: referrer };
  }
}

function filterNullValues<T extends Record<string, unknown>>(obj: T): Record<string, unknown> {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== null));
}

function extractAttributionData(): AttributionData {
  const utmSource = getUrlParam('utm_source');
  const utmMedium = getUrlParam('utm_medium');
  const utmCampaign = getUrlParam('utm_campaign');
  const utmContent = getUrlParam('utm_content');
  const refParam = getUrlParam('ref');
  const referrerParsed = parseReferrer(document.referrer);

  return {
    referrer_type: referrerParsed.type,
    ...(referrerParsed.domain && { referrer_domain: referrerParsed.domain }),
    ...(referrerParsed.full && { referrer_url: referrerParsed.full }),
    ...(utmSource && { utm_source: utmSource }),
    ...(utmMedium && { utm_medium: utmMedium }),
    ...(utmCampaign && { utm_campaign: utmCampaign }),
    ...(utmContent && { utm_content: utmContent }),
    ...(refParam && { ref_param: refParam }),
    landing_path: window.location.pathname,
    landing_url: window.location.href,
    first_seen_at: new Date().toISOString(),
  };
}

function getFirstTouchAttribution(): AttributionData {
  const stored = localStorage.getItem(STORAGE_KEYS.FIRST_TOUCH);
  if (stored) {
    try { return JSON.parse(stored) as AttributionData; } catch (e) {
      log('Failed to parse stored first_touch:', e);
    }
  }
  const firstTouch = extractAttributionData();
  localStorage.setItem(STORAGE_KEYS.FIRST_TOUCH, JSON.stringify(firstTouch));
  log('Established first-touch attribution:', firstTouch);
  return firstTouch;
}

function getSessionAttribution(): AttributionData {
  const sessionData = extractAttributionData();
  sessionStorage.setItem(STORAGE_KEYS.SESSION_REFERRER, JSON.stringify(sessionData));
  return sessionData;
}

function extractAgentHandle(): string | null {
  const match = window.location.pathname.match(/\/agent\/([^\/]+)/);
  return match?.[1] ?? null;
}

function buildUserProperties(): Record<string, unknown> {
  const firstTouch = getFirstTouchAttribution();
  const sessionData = getSessionAttribution();
  const primarySource: string =
    firstTouch.utm_source ?? firstTouch.ref_param ?? firstTouch.referrer_type ?? 'direct';
  const agentHandle = extractAgentHandle();

  const userProperties = {
    acquisition_source: primarySource,
    ...(firstTouch.utm_medium && { acquisition_medium: firstTouch.utm_medium }),
    ...(firstTouch.utm_campaign && { acquisition_campaign: firstTouch.utm_campaign }),
    ...(firstTouch.referrer_domain && { acquisition_referrer: firstTouch.referrer_domain }),
    first_touch_type: firstTouch.referrer_type || 'direct',
    first_touch_path: firstTouch.landing_path || '/',
    first_touch_timestamp: firstTouch.first_seen_at || new Date().toISOString(),
    ...(sessionData.referrer_type && { session_referrer_type: sessionData.referrer_type }),
    ...(sessionData.referrer_domain && { session_referrer_domain: sessionData.referrer_domain }),
    ...(sessionData.landing_path && { session_landing_page: sessionData.landing_path }),
    agentfolio_page: window.location.pathname.startsWith('/agent/') ? 'profile' : 'listing',
    ...(agentHandle && { agent_handle: agentHandle }),
  };

  return filterNullValues(userProperties);
}

function initializePostHog(): Promise<void> {
  if (typeof window.posthog !== 'undefined') {
    log('PostHog already initialized');
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = 'https://us.i.posthog.com/static/array.js';
    document.head.appendChild(script);

    script.onload = () => {
      window.posthog?.init(CONFIG.POSTHOG_API_KEY, {
        api_host: CONFIG.POSTHOG_HOST,
        loaded: () => { log('PostHog initialized'); resolve(); },
      });
    };
  });
}

function syncUserProperties(): void {
  if (typeof window.posthog === 'undefined') {
    log('PostHog not available for sync');
    return;
  }
  const userProps = buildUserProperties();
  log('Syncing user properties:', userProps);
  const alreadySynced = sessionStorage.getItem(STORAGE_KEYS.ATTRIBUTION_SYNCED);

  if (!alreadySynced) {
    window.posthog.people.set(userProps);
    log('Set user properties (first sync this session)');
    sessionStorage.setItem(STORAGE_KEYS.ATTRIBUTION_SYNCED, 'true');
  } else {
    window.posthog.register(userProps);
    log('Registered properties (already synced this session)');
  }

  if (document.referrer && document.referrer !== '') {
    const refData = parseReferrer(document.referrer);
    window.posthog.capture('referral_detected', {
      referrer_type: refData.type,
      referrer_domain: refData.domain,
      landing_page: window.location.pathname,
    });
  }
}

function trackPageView(): void {
  if (typeof window.posthog === 'undefined') return;
  const agentHandle = extractAgentHandle();
  const pageviewProps: AnalyticsEventProperties = {
    page_title: document.title,
    $current_url: window.location.href,
    $pathname: window.location.pathname,
    agentfolio_agent: agentHandle,
    agentfolio_page_type: agentHandle ? 'profile' : 'listing',
    ...(agentHandle && { profile_viewed: agentHandle }),
  };
  window.posthog.capture('$pageview', pageviewProps);
  if (agentHandle) {
    window.posthog.capture('agent_profile_viewed', {
      agent_handle: agentHandle,
      referrer_type: getFirstTouchAttribution().referrer_type || 'direct',
    });
  }
}

function initializeAnalyticsAPI(): void {
  window.AgentFolioAnalytics = {
    trackEvent: (eventName: string, properties: AnalyticsEventProperties = {}) => {
      if (typeof window.posthog !== 'undefined') {
        window.posthog.capture(eventName, properties);
      }
    },
    trackPlatformClick: (platform: string, url: string) => {
      window.AgentFolioAnalytics.trackEvent('platform_link_clicked', {
        platform, url,
        agent_handle: extractAgentHandle(),
        referrer_at_click: getFirstTouchAttribution().referrer_type,
      });
    },
    trackShare: (shareMethod: string) => {
      window.AgentFolioAnalytics.trackEvent('profile_shared', {
        share_method: shareMethod,
        agent_handle: extractAgentHandle(),
      });
    },
    getAttribution: getFirstTouchAttribution,
  };
}

function attachLinkTracking(): void {
  document.querySelectorAll('a[href^="http"]').forEach((link) => {
    link.addEventListener('click', function (this: HTMLAnchorElement) {
      const href = this.href;
      let platform = 'external';
      if (href.includes('github.com')) platform = 'github';
      else if (href.includes('twitter.com') || href.includes('x.com')) platform = 'x';
      else if (href.includes('moltbook.com') || href.includes('moltlaunch.com')) platform = 'moltbook';
      else if (href.includes('toku.agency')) platform = 'toku';
      window.AgentFolioAnalytics.trackPlatformClick(platform, href);
    });
  });
}

async function init(): Promise<void> {
  log('Initializing referral tracker...');
  try {
    initializeAnalyticsAPI();
    await initializePostHog();
    syncUserProperties();
    trackPageView();
    attachLinkTracking();
    log('Referral tracker initialized successfully');
  } catch (e) {
    console.error('[AF Referral] Initialization error:', e);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => { void init(); });
} else {
  void init();
}

let lastUrl = location.href;
new MutationObserver(() => {
  const url = location.href;
  if (url !== lastUrl) {
    lastUrl = url;
    setTimeout(trackPageView, 100);
  }
}).observe(document, { subtree: true, childList: true });

export {
  CONFIG,
  STORAGE_KEYS,
  type AttributionData,
  type ReferrerData,
  type UserProperties,
  type AgentFolioAnalyticsAPI,
  getFirstTouchAttribution,
  extractAttributionData,
  parseReferrer,
  extractAgentHandle,
};
