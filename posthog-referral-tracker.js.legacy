/**
 * AgentFolio PostHog Referral Tracker v2.0
 * Tracks referral sources and persists them as user properties
 * 
 * Features:
 * - First-touch attribution via localStorage
 * - UTM parameter tracking  
 * - Document.referrer analysis
 * - PostHog user property syncing
 */

(function() {
    'use strict';
    
    // Configuration
    const CONFIG = {
        POSTHOG_API_KEY: 'phc_YOUR_PROJECT_API_KEY_HERE',
        POSTHOG_HOST: 'https://us.i.posthog.com',
        DEBUG: false
    };
    
    // Storage keys
    const STORAGE_KEYS = {
        FIRST_TOUCH: 'af_first_touch',
        SESSION_REFERRER: 'af_session_referrer',
        ATTRIBUTION_SYNCED: 'af_attribution_synced'
    };
    
    // Debug logger
    function log(...args) {
        if (CONFIG.DEBUG) console.log('[AF Referral]', ...args);
    }
    
    /**
     * Parse URL parameters
     */
    function getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }
    
    /**
     * Parse and categorize referrer
     */
    function parseReferrer(referrer) {
        if (!referrer || referrer === 'null' || referrer === '') {
            return { type: 'direct', domain: null, full: null };
        }
        
        try {
            const url = new URL(referrer);
            const domain = url.hostname.toLowerCase().replace(/^www\./, '');
            
            // Social platforms
            const social = ['twitter.com', 'x.com', 'facebook.com', 'fb.com', 'linkedin.com', 'reddit.com', 'bluesky.io', 'mastodon.social', 'instagram.com'];
            // Search engines
            const search = ['google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com', 'ecosia.org', 'kagi.com', 'yandex.com', 'baidu.com'];
            // Developer/SaaS platforms
            const dev = ['github.com', 'producthunt.com', 'hackernews.ycombinator.com', 'news.ycombinator.com', 'dev.to', 'medium.com'];
            
            if (social.some(s => domain.includes(s))) return { type: 'social', domain, full: referrer };
            if (search.some(s => domain.includes(s))) return { type: 'search', domain, full: referrer };
            if (dev.some(d => domain.includes(d))) return { type: 'developer', domain, full: referrer };
            
            return { type: 'referral', domain, full: referrer };
        } catch (e) {
            return { type: 'unknown', domain: null, full: referrer };
        }
    }
    
    /**
     * Extract all attribution data from URL and document
     */
    function extractAttributionData() {
        const utmSource = getUrlParam('utm_source');
        const utmMedium = getUrlParam('utm_medium');
        const utmCampaign = getUrlParam('utm_campaign');
        const utmContent = getUrlParam('utm_content');
        const refParam = getUrlParam('ref');
        const referrerParsed = parseReferrer(document.referrer);
        
        const data = {
            // UTM parameters (highest priority)
            utm_source: utmSource,
            utm_medium: utmMedium,
            utm_campaign: utmCampaign,
            utm_content: utmContent,
            
            // Explicit ref parameter
            ref_param: refParam,
            
            // Referrer data
            referrer_type: referrerParsed.type,
            referrer_domain: referrerParsed.domain,
            referrer_url: referrerParsed.full,
            
            // Current page context
            landing_path: window.location.pathname,
            landing_url: window.location.href,
            
            // Timestamp
            first_seen_at: new Date().toISOString()
        };
        
        // Remove null values
        return Object.fromEntries(Object.entries(data).filter(([_, v]) => v !== null));
    }
    
    /**
     * Get or establish first-touch attribution
     */
    function getFirstTouchAttribution() {
        const stored = localStorage.getItem(STORAGE_KEYS.FIRST_TOUCH);
        
        if (stored) {
            try {
                return JSON.parse(stored);
            } catch (e) {
                log('Failed to parse stored first_touch:', e);
            }
        }
        
        // Establish first-touch
        const firstTouch = extractAttributionData();
        localStorage.setItem(STORAGE_KEYS.FIRST_TOUCH, JSON.stringify(firstTouch));
        log('Established first-touch attribution:', firstTouch);
        return firstTouch;
    }
    
    /**
     * Get session attribution (refreshes each session)
     */
    function getSessionAttribution() {
        const sessionData = extractAttributionData();
        sessionStorage.setItem(STORAGE_KEYS.SESSION_REFERRER, JSON.stringify(sessionData));
        return sessionData;
    }
    
    /**
     * Build user properties for PostHog
     */
    function buildUserProperties() {
        const firstTouch = getFirstTouchAttribution();
        const sessionData = getSessionAttribution();
        
        // Determine primary source (utm_source > ref_param > referrer_type)
        const primarySource = firstTouch.utm_source 
            || firstTouch.ref_param 
            || firstTouch.referrer_type 
            || 'direct';
        
        const userProperties = {
            // First-touch attribution (persisted on user)
            acquisition_source: primarySource,
            acquisition_medium: firstTouch.utm_medium || null,
            acquisition_campaign: firstTouch.utm_campaign || null,
            acquisition_referrer: firstTouch.referrer_domain || firstTouch.referrer_type || null,
            first_touch_type: firstTouch.referrer_type || 'direct',
            first_touch_path: firstTouch.landing_path || '/',
            first_touch_timestamp: firstTouch.first_seen_at || new Date().toISOString(),
            
            // Current session attribution
            session_referrer_type: sessionData.referrer_type,
            session_referrer_domain: sessionData.referrer_domain,
            session_landing_page: sessionData.landing_path,
            
            // AgentFolio specific
            agentfolio_page: window.location.pathname.startsWith('/agent/') ? 'profile' : 'listing',
            agent_handle: extractAgentHandle()
        };
        
        // Clean null values
        return Object.fromEntries(Object.entries(userProperties).filter(([_, v]) => v !== null));
    }
    
    /**
     * Extract agent handle from URL if on profile page
     */
    function extractAgentHandle() {
        const match = window.location.pathname.match(/\/agent\/([^\/]+)/);
        return match ? match[1] : null;
    }
    
    /**
     * Initialize PostHog if not already loaded
     */
    function initializePostHog() {
        if (typeof posthog !== 'undefined') {
            log('PostHog already initialized');
            return Promise.resolve();
        }
        
        return new Promise((resolve, reject) => {
            // PostHog loader snippet
            !function(t,e){var o,n,p,r;e.__SV=1,window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=""+(e=".")),e},u.people.toString=function(){return u.toString(1)+".people"},o="capture identify alias people.set people.set_once register register_once unregister opt_out_capturing opt_in_capturing has_opted_in_capturing has_opted_out_capturing opt_in_capturing_by_default".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1}(document,window.posthog||[]);
            
            posthog.init(CONFIG.POSTHOG_API_KEY, {
                api_host: CONFIG.POSTHOG_HOST,
                loaded: function(posthog) {
                    log('PostHog initialized');
                    resolve();
                }
            });
        });
    }
    
    /**
     * Sync user properties to PostHog
     */
    function syncUserProperties() {
        if (typeof posthog === 'undefined') {
            log('PostHog not available for sync');
            return;
        }
        
        const userProps = buildUserProperties();
        log('Syncing user properties:', userProps);
        
        // Set persistent user properties (only sync once per session to avoid overwriting)
        const alreadySynced = sessionStorage.getItem(STORAGE_KEYS.ATTRIBUTION_SYNCED);
        
        if (!alreadySynced) {
            // First sync - set_once for attribution data
            posthog.people.set(userProps);
            log('Set user properties (first sync this session)');
            sessionStorage.setItem(STORAGE_KEYS.ATTRIBUTION_SYNCED, 'true');
        } else {
            // Subsequent sync - only update session-level properties
            posthog.register(userProps);
            log('Registered properties (already synced this session)');
        }
        
        // Track referral event if there's a referrer
        if (document.referrer && document.referrer !== '') {
            const refData = parseReferrer(document.referrer);
            posthog.capture('referral_detected', {
                referrer_type: refData.type,
                referrer_domain: refData.domain,
                landing_page: window.location.pathname
            });
        }
    }
    
    /**
     * Track page view with attribution context
     */
    function trackPageView() {
        if (typeof posthog === 'undefined') return;
        
        const agentHandle = extractAgentHandle();
        
        posthog.capture('$pageview', {
            page_title: document.title,
            $current_url: window.location.href,
            $pathname: window.location.pathname,
            agentfolio_agent: agentHandle,
            agentfolio_page_type: agentHandle ? 'profile' : 'listing',
            ...(agentHandle && { profile_viewed: agentHandle })
        });
        
        // Track specific agent profile views
        if (agentHandle) {
            posthog.capture('agent_profile_viewed', {
                agent_handle: agentHandle,
                referrer_type: getFirstTouchAttribution().referrer_type || 'direct'
            });
        }
    }
    
    /**
     * Expose analytics API for manual tracking
     */
    window.AgentFolioAnalytics = {
        trackEvent: function(eventName, properties = {}) {
            if (typeof posthog !== 'undefined') {
                posthog.capture(eventName, properties);
            }
        },
        
        trackPlatformClick: function(platform, url) {
            this.trackEvent('platform_link_clicked', {
                platform: platform,
                url: url,
                agent_handle: extractAgentHandle(),
                referrer_at_click: getFirstTouchAttribution().referrer_type
            });
        },
        
        trackShare: function(shareMethod) {
            this.trackEvent('profile_shared', {
                share_method: shareMethod,
                agent_handle: extractAgentHandle()
            });
        },
        
        getAttribution: getFirstTouchAttribution
    };
    
    /**
     * Auto-attach click tracking to platform links
     */
    function attachLinkTracking() {
        document.querySelectorAll('a[href^="http"]').forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.href;
                let platform = 'external';
                
                if (href.includes('github.com')) platform = 'github';
                else if (href.includes('twitter.com') || href.includes('x.com')) platform = 'x';
                else if (href.includes('moltbook.com') || href.includes('moltlaunch.com')) platform = 'moltbook';
                else if (href.includes('toku.agency')) platform = 'toku';
                
                AgentFolioAnalytics.trackPlatformClick(platform, href);
            });
        });
    }
    
    /**
     * Initialize everything
     */
    async function init() {
        log('Initializing referral tracker...');
        
        try {
            await initializePostHog();
            syncUserProperties();
            trackPageView();
            attachLinkTracking();
            
            log('Referral tracker initialized successfully');
        } catch (e) {
            console.error('[AF Referral] Initialization error:', e);
        }
    }
    
    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Re-run tracking when URL changes (SPA-style navigation)
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(trackPageView, 100);
        }
    }).observe(document, { subtree: true, childList: true });
    
})();
