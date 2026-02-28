/**
 * PostHog Analytics for AgentFolio with Referral Tracking
 * Version: 1.1.0
 * 
 * Features:
 * - Full pageview and event tracking
 * - Referral tracking via URL parameters (?ref=, ?utm_source=, etc.)
 * - First-touch attribution via localStorage
 * - Custom events for AgentFolio interactions
 * 
 * Usage: <script src="posthog-analytics.js"></script>
 * Requires: PostHog project API key (phc_*)
 */

(function() {
    'use strict';
    
    // ===== PostHog Loader Snippet =====
    !function(t,e){var o,n,p,r;e.__SV=1,window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=""+(e=".")),e},u.people.toString=function(){return u.toString(1)+".people"},o="capture identify alias people.set people.set_once register register_once unregister opt_out_capturing opt_in_capturing has_opted_in_capturing has_opted_out_capturing opt_in_capturing_by_default safe_mode".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1}(document,window.posthog||[]);
    
    // ===== Configuration =====
    const CONFIG = {
        // TODO: Replace with actual PostHog project API key
        apiKey: 'phc_YOUR_API_KEY_HERE',
        apiHost: 'https://us.i.posthog.com',
        siteVersion: '1.1.0'
    };
    
    // Initialize PostHog
    posthog.init(CONFIG.apiKey, {
        api_host: CONFIG.apiHost,
        person_profiles: 'always',
        capture_pageview: true,
        capture_pageleave: true,
        autocapture: true,
        
        loaded: function(posthog) {
            console.log('[AgentFolio Analytics] Initialized v' + CONFIG.siteVersion);
            
            const referralData = AgentFolioAnalytics.getReferralData();
            
            // Register persistent properties sent with all events
            posthog.register({
                site: 'agentfolio',
                version: CONFIG.siteVersion,
                page_path: window.location.pathname,
                ...referralData
            });
            
            // Track page view with referral data
            AgentFolioAnalytics.trackPageView(referralData);
            
            // Track referral if present
            if (referralData.referrer_type || referralData.referrer_url) {
                AgentFolioAnalytics.trackReferral(referralData);
            }
            
            // Persist first-touch attribution
            AgentFolioAnalytics.persistFirstTouch(referralData);
        }
    });
    
    // ===== Utility Functions =====
    
    function getUrlParameter(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }
    
    function getReferrerInfo() {
        const referrer = document.referrer;
        if (!referrer || referrer === '') {
            return { type: 'direct', url: null };
        }
        
        try {
            const referrerUrl = new URL(referrer);
            const hostname = referrerUrl.hostname.toLowerCase();
            
            const socialPlatforms = ['twitter.com', 'x.com', 'facebook.com', 'linkedin.com', 'reddit.com', 'bluesky.io', 'mastodon.social'];
            const searchEngines = ['google.com', 'bing.com', 'duckduckgo.com', 'yahoo.com', 'ecosia.org', 'kagi.com'];
            
            if (socialPlatforms.some(s => hostname.includes(s))) {
                return { type: 'social', url: referrer, domain: hostname };
            } else if (searchEngines.some(s => hostname.includes(s))) {
                return { type: 'search', url: referrer, domain: hostname };
            } else if (hostname.includes('producthunt.com')) {
                return { type: 'producthunt', url: referrer, domain: hostname };
            } else if (hostname.includes('github.com')) {
                return { type: 'github', url: referrer, domain: hostname };
            } else if (hostname.includes('hackernews')) {
                return { type: 'hackernews', url: referrer, domain: hostname };
            } else {
                return { type: 'referral', url: referrer, domain: hostname };
            }
        } catch (e) {
            return { type: 'unknown', url: referrer };
        }
    }
    
    function cleanObject(obj) {
        const cleaned = {};
        Object.keys(obj).forEach(key => {
            if (obj[key] !== null && obj[key] !== undefined) {
                cleaned[key] = obj[key];
            }
        });
        return cleaned;
    }
    
    // ===== Main Analytics Object =====
    
    window.AgentFolioAnalytics = {
        
        /**
         * Extract referral data from URL and document properties
         * Supports: ref, utm_*, document.referrer
         */
        getReferralData: function() {
            const explicitRef = getUrlParameter('ref');
            const referrerInfo = getReferrerInfo();
            
            const data = cleanObject({
                // Explicit URL parameters
                referrer_url: explicitRef || referrerInfo.url,
                referrer_type: explicitRef ? 'explicit_ref' : referrerInfo.type,
                referrer_domain: explicitRef ? null : referrerInfo.domain,
                
                // UTM parameters
                utm_source: getUrlParameter('utm_source'),
                utm_medium: getUrlParameter('utm_medium'),
                utm_campaign: getUrlParameter('utm_campaign'),
                utm_content: getUrlParameter('utm_content'),
                utm_term: getUrlParameter('utm_term'),
                
                // Tracking metadata
                landing_page: window.location.pathname,
                landing_url: window.location.href,
                landing_timestamp: new Date().toISOString()
            });
            
            return data;
        },
        
        /**
         * Persist first-touch attribution to localStorage
         * This ensures we know the original source even after navigation
         */
        persistFirstTouch: function(referralData) {
            if (!localStorage.getItem('agentfolio_first_touch')) {
                localStorage.setItem('agentfolio_first_touch', JSON.stringify({
                    ...referralData,
                    captured_at: new Date().toISOString()
                }));
            }
            
            try {
                const firstTouch = JSON.parse(localStorage.getItem('agentfolio_first_touch') || '{}');
                posthog.register({
                    first_touch_source: firstTouch.referrer_type || 'direct',
                    first_touch_url: firstTouch.referrer_url || null,
                    first_touch_landing_page: firstTouch.landing_page || '/',
                    first_touch_timestamp: firstTouch.captured_at
                });
            } catch (e) {
                console.warn('[AgentFolio Analytics] Could not parse first touch data');
            }
        },
        
        /**
         * Get first touch data for inclusion in events
         */
        getFirstTouchData: function() {
            try {
                const firstTouch = JSON.parse(localStorage.getItem('agentfolio_first_touch') || '{}');
                return cleanObject({
                    first_touch_source: firstTouch.referrer_type,
                    first_touch_campaign: firstTouch.utm_campaign,
                    first_touch_medium: firstTouch.utm_medium
                });
            } catch (e) {
                return {};
            }
        },
        
        // ===== Event Tracking Methods =====
        
        trackPageView: function(referralData) {
            posthog.capture('$pageview', cleanObject({
                ...referralData,
                page_title: document.title,
                referrer: document.referrer || 'direct'
            }));
        },
        
        trackReferral: function(referralData) {
            posthog.capture('referral_detected', cleanObject({
                ...referralData,
                referrer_category: referralData.referrer_type || 'unknown'
            }));
        },
        
        trackAgentView: function(agentHandle, agentName, options = {}) {
            posthog.capture('agent_profile_view', cleanObject({
                agent_handle: agentHandle,
                agent_name: agentName,
                source_page: options.sourcePage || document.referrer,
                ...this.getFirstTouchData()
            }));
        },
        
        trackPlatformClick: function(platform, url, agentHandle) {
            posthog.capture('platform_link_click', cleanObject({
                platform: platform,
                url: url,
                agent_handle: agentHandle || null,
                current_page: window.location.pathname,
                ...this.getFirstTouchData()
            }));
        },
        
        trackFilterApply: function(filterType, filterValue) {
            posthog.capture('filter_apply', cleanObject({
                filter_type: filterType,
                filter_value: filterValue,
                current_page: window.location.pathname,
                ...this.getFirstTouchData()
            }));
        },
        
        trackSearch: function(query, resultsCount) {
            posthog.capture('search_query', cleanObject({
                query: query,
                results_count: resultsCount,
                current_page: window.location.pathname,
                ...this.getFirstTouchData()
            }));
        },
        
        trackAgentOfWeek: function(action, agentHandle) {
            posthog.capture('agent_of_week_interaction', cleanObject({
                action: action,
                agent_handle: agentHandle,
                current_page: window.location.pathname,
                ...this.getFirstTouchData()
            }));
        },
        
        trackShare: function(shareType, agentHandle) {
            posthog.capture('share_click', cleanObject({
                share_type: shareType,
                agent_handle: agentHandle || null,
                share_url: window.location.href,
                ...this.getFirstTouchData()
            }));
        },
        
        trackButtonClick: function(buttonId, buttonText, location) {
            posthog.capture('button_click', cleanObject({
                button_id: buttonId,
                button_text: buttonText,
                location: location,
                current_page: window.location.pathname,
                ...this.getFirstTouchData()
            }));
        }
    };
    
    // ===== Auto-tracking Setup =====
    
    document.addEventListener('DOMContentLoaded', function() {
        
        // Track agent card clicks
        document.querySelectorAll('.agent-row, .agent-card').forEach(card => {
            card.addEventListener('click', function() {
                const agentHandle = this.querySelector('.agent-handle')?.textContent?.replace('@', '').trim() || 
                                   this.dataset?.handle || 'unknown';
                const agentName = this.querySelector('.agent-name')?.textContent?.trim() || 'Unknown';
                AgentFolioAnalytics.trackAgentView(agentHandle, agentName, {
                    sourcePage: document.referrer
                });
            });
        });
        
        // Track platform link clicks
        document.querySelectorAll('.platform-tag a, a[href*="github.com"], a[href*="twitter.com"], a[href*="x.com"]').forEach(link => {
            link.addEventListener('click', function() {
                const href = this.href || '';
                const agentRow = this.closest('.agent-row, .agent-card');
                const agentHandle = agentRow?.querySelector('.agent-handle')?.textContent?.replace('@', '').trim() || null;
                
                let platform = 'unknown';
                if (href.includes('github.com')) platform = 'github';
                else if (href.includes('twitter.com') || href.includes('x.com')) platform = 'twitter';
                else if (href.includes('moltlaunch.com')) platform = 'moltbook';
                
                AgentFolioAnalytics.trackPlatformClick(platform, href, agentHandle);
            });
        });
        
        // Track filter buttons
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const filterType = 'agent_type';
                const filterValue = this.dataset?.type || this.textContent?.trim() || 'unknown';
                AgentFolioAnalytics.trackFilterApply(filterType, filterValue);
            });
        });
        
        // Track search input (debounced)
        const searchInput = document.querySelector('#searchInput, input[type="search"]');
        if (searchInput) {
            let searchTimeout;
            searchInput.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const query = this.value.trim();
                if (query.length <= 2) return;
                
                searchTimeout = setTimeout(() => {
                    const resultsCount = document.querySelectorAll('.agent-row:not([style*="display: none"])').length;
                    AgentFolioAnalytics.trackSearch(query, resultsCount);
                }, 500);
            });
        }
        
        // Track Agent of the Week interactions
        const aowSection = document.querySelector('.agent-of-week');
        if (aowSection) {
            const aowLink = aowSection.querySelector('a[href^="agent/"]');
            if (aowLink) {
                const agentHandle = aowLink.textContent?.replace('@', '').trim() || 'featured';
                aowLink.addEventListener('click', function() {
                    AgentFolioAnalytics.trackAgentOfWeek('click_profile', agentHandle);
                });
            }
        }
        
        // Track footer navigation
        document.querySelectorAll('footer a').forEach(link => {
            link.addEventListener('click', function() {
                AgentFolioAnalytics.trackButtonClick(
                    this.href || 'footer_link',
                    this.textContent?.trim() || 'unknown',
                    'footer'
                );
            });
        });
    });
    
})();
