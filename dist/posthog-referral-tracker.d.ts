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
    people: {
        set: (properties: Record<string, unknown>) => void;
    };
    register: (properties: Record<string, unknown>) => void;
}
interface PostHogConfig {
    api_host: string;
    loaded?: () => void;
}
declare const CONFIG: Config;
declare const STORAGE_KEYS: StorageKeys;
declare function parseReferrer(referrer: string | null): ReferrerData;
declare function extractAttributionData(): AttributionData;
declare function getFirstTouchAttribution(): AttributionData;
declare function extractAgentHandle(): string | null;
export { CONFIG, STORAGE_KEYS, type AttributionData, type ReferrerData, type UserProperties, type AgentFolioAnalyticsAPI, getFirstTouchAttribution, extractAttributionData, parseReferrer, extractAgentHandle, };
//# sourceMappingURL=posthog-referral-tracker.d.ts.map