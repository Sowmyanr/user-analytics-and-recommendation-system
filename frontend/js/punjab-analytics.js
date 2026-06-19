/**
 * Punjab Rozgar Analytics Library
 * Integrates with the FastAPI backend analytics system
 */
class PunjabRozgarAnalytics {
    constructor(options = {}) {
        this.apiUrl = options.apiUrl || 'http://localhost:8000/api/v1';
        this.sessionId = this.generateSessionId();
        this.userId = this.getUserId();
        this.eventQueue = [];
        this.isInitialized = false;
        this.debug = options.debug || false;
        
        this.init();
    }

    init() {
        if (this.isInitialized) return;
        
        this.log('Initializing Punjab Rozgar Analytics...');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.startTracking());
        } else {
            this.startTracking();
        }
        
        this.isInitialized = true;
    }

    startTracking() {
        // Track page load
        this.trackPageView();
        
        // Track user interactions
        this.setupEventListeners();
        
        // Start session tracking
        this.startSession();
        
        // Flush events periodically
        this.flushInterval = setInterval(() => this.flushEvents(), 5000);
        
        // Flush on page unload
        window.addEventListener('beforeunload', () => this.flush());
        
        this.log('Analytics tracking started');
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    getUserId() {
        let userId = localStorage.getItem('punjab_rozgar_user_id');
        if (!userId) {
            userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('punjab_rozgar_user_id', userId);
        }
        return userId;
    }

    log(message, data = null) {
        if (this.debug) {
            console.log(`[Punjab Rozgar Analytics] ${message}`, data);
        }
    }

    // Track page views
    trackPageView() {
        const eventData = {
            event_type: 'page_view',
            event_name: 'Page View',
            page_url: window.location.pathname,
            page_title: document.title,
            referrer: document.referrer,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                user_agent: navigator.userAgent,
                screen_resolution: `${screen.width}x${screen.height}`,
                viewport_size: `${window.innerWidth}x${window.innerHeight}`,
                language: navigator.language,
                platform: navigator.platform,
                url: window.location.href,
                path: window.location.pathname,
                search: window.location.search,
                hash: window.location.hash
            }
        };
        
        this.queueEvent(eventData);
        this.log('Page view tracked', eventData);
    }

    // Track custom events
    track(eventName, properties = {}) {
        const eventData = {
            event_type: 'custom',
            event_name: eventName,
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                ...properties,
                page_title: document.title
            }
        };
        
        this.queueEvent(eventData);
        this.log(`Custom event tracked: ${eventName}`, eventData);
    }

    // Track job interactions
    trackJobInteraction(jobId, interactionType, properties = {}) {
        const eventData = {
            event_type: 'job_interaction',
            event_name: `Job ${interactionType}`,
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                job_id: jobId,
                interaction_type: interactionType,
                ...properties
            }
        };
        
        this.queueEvent(eventData);
        this.log(`Job interaction tracked: ${interactionType} for job ${jobId}`, eventData);
    }

    // Track user registration/login
    trackUserAuth(action, properties = {}) {
        const eventData = {
            event_type: 'user_auth',
            event_name: `User ${action}`,
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                auth_action: action,
                ...properties
            }
        };
        
        this.queueEvent(eventData);
        this.log(`User auth tracked: ${action}`, eventData);
    }

    // Track form submissions
    trackFormSubmission(formName, formData = {}) {
        const eventData = {
            event_type: 'form_submission',
            event_name: `Form Submitted: ${formName}`,
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                form_name: formName,
                form_data: formData
            }
        };
        
        this.queueEvent(eventData);
        this.log(`Form submission tracked: ${formName}`, eventData);
    }

    // Track search queries
    trackSearch(searchQuery, results = 0, filters = {}) {
        const eventData = {
            event_type: 'search',
            event_name: 'Search Performed',
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                search_query: searchQuery,
                results_count: results,
                filters: filters
            }
        };
        
        this.queueEvent(eventData);
        this.log(`Search tracked: "${searchQuery}"`, eventData);
    }

    // Setup automatic event listeners
    setupEventListeners() {
        // Track clicks
        document.addEventListener('click', (event) => {
            const element = event.target;
            
            // Track button clicks
            if (element.tagName === 'BUTTON' || element.type === 'button') {
                this.track('Button Click', {
                    button_text: element.textContent?.trim() || element.value,
                    button_id: element.id,
                    button_class: element.className,
                    button_type: element.type
                });
            }
            
            // Track link clicks
            if (element.tagName === 'A') {
                this.track('Link Click', {
                    link_text: element.textContent?.trim(),
                    link_url: element.href,
                    link_id: element.id,
                    is_external: element.hostname !== window.location.hostname
                });
            }
            
            // Track job-related clicks
            if (element.closest('[data-job-id]')) {
                const jobId = element.closest('[data-job-id]').dataset.jobId;
                const jobTitle = element.closest('[data-job-id]').dataset.jobTitle || 'Unknown';
                this.trackJobInteraction(jobId, 'view', {
                    job_title: jobTitle,
                    element_type: element.tagName,
                    element_text: element.textContent?.trim()
                });
            }

            // Track navigation clicks
            if (element.closest('nav') || element.closest('.nav') || element.closest('.navbar')) {
                this.track('Navigation Click', {
                    nav_item: element.textContent?.trim(),
                    nav_url: element.href
                });
            }
        });

        // Track form submissions
        document.addEventListener('submit', (event) => {
            const form = event.target;
            const formData = new FormData(form);
            const formObject = {};
            
            // Convert FormData to object (excluding sensitive fields)
            for (let [key, value] of formData.entries()) {
                if (!key.toLowerCase().includes('password') && 
                    !key.toLowerCase().includes('secret') &&
                    !key.toLowerCase().includes('token')) {
                    formObject[key] = value;
                }
            }
            
            const formName = form.id || form.className || form.name || 'unknown';
            this.trackFormSubmission(formName, formObject);
        });

        // Track scroll depth
        let maxScroll = 0;
        window.addEventListener('scroll', () => {
            const scrollPercent = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
            if (scrollPercent > maxScroll && scrollPercent % 25 === 0) {
                maxScroll = scrollPercent;
                this.track('Scroll Depth', { 
                    scroll_percent: scrollPercent,
                    page_height: document.body.scrollHeight
                });
            }
        });

        // Track time on page
        this.startTime = Date.now();
        window.addEventListener('beforeunload', () => {
            const timeOnPage = Math.round((Date.now() - this.startTime) / 1000);
            this.track('Time on Page', { 
                time_seconds: timeOnPage,
                time_minutes: Math.round(timeOnPage / 60)
            });
        });
    }

    // Start session tracking
    startSession() {
        const sessionData = {
            event_type: 'session_start',
            event_name: 'Session Started',
            page_url: window.location.pathname,
            session_id: this.sessionId,
            user_id: this.userId,
            timestamp: new Date().toISOString(),
            properties: {
                landing_page: window.location.pathname,
                referrer: document.referrer,
                utm_source: this.getUrlParameter('utm_source'),
                utm_medium: this.getUrlParameter('utm_medium'),
                utm_campaign: this.getUrlParameter('utm_campaign'),
                utm_content: this.getUrlParameter('utm_content'),
                utm_term: this.getUrlParameter('utm_term'),
                browser: this.getBrowserInfo(),
                device_type: this.getDeviceType()
            }
        };
        
        this.queueEvent(sessionData);
        this.log('Session started', sessionData);
    }

    // Get URL parameters
    getUrlParameter(name) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(name);
    }

    // Get browser info
    getBrowserInfo() {
        const userAgent = navigator.userAgent;
        if (userAgent.includes('Chrome')) return 'Chrome';
        if (userAgent.includes('Firefox')) return 'Firefox';
        if (userAgent.includes('Safari')) return 'Safari';
        if (userAgent.includes('Edge')) return 'Edge';
        if (userAgent.includes('Opera')) return 'Opera';
        return 'Unknown';
    }

    // Get device type
    getDeviceType() {
        if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
            return 'Mobile';
        }
        if (/iPad/i.test(navigator.userAgent)) {
            return 'Tablet';
        }
        return 'Desktop';
    }

    // Queue events for batch sending
    queueEvent(eventData) {
        this.eventQueue.push(eventData);
        
        // Send immediately if queue is full
        if (this.eventQueue.length >= 10) {
            this.flushEvents();
        }
    }

    // Send queued events to backend
    async flushEvents() {
        if (this.eventQueue.length === 0) return;
        
        const events = [...this.eventQueue];
        this.eventQueue = [];
        
        try {
            // Send each event individually since the API expects single events
            for (const event of events) {
                const response = await fetch(`${this.apiUrl}/analytics/track`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        event: event.event_name,
                        properties: {
                            ...event.properties,
                            event_type: event.event_type,
                            page_url: event.page_url,
                            session_id: event.session_id,
                            user_id: event.user_id,
                            timestamp: event.timestamp
                        },
                        user_id: event.user_id,
                        session_id: event.session_id,
                        timestamp: event.timestamp
                    })
                });
                
                if (!response.ok) {
                    this.log('Analytics tracking failed for event:', event);
                    // Re-queue failed event
                    this.eventQueue.push(event);
                } else {
                    this.log('Successfully sent analytics event:', event.event_name);
                }
            }
        } catch (error) {
            this.log('Analytics tracking error:', error);
            // Re-queue all events if there was a network error
            this.eventQueue.unshift(...events);
        }
    }

    // Manual flush for page unload
    flush() {
        if (this.eventQueue.length > 0) {
            // Use sendBeacon for reliable sending on page unload
            if (navigator.sendBeacon) {
                navigator.sendBeacon(
                    `${this.apiUrl}/analytics/track`,
                    JSON.stringify({ events: this.eventQueue })
                );
            } else {
                // Fallback to synchronous request
                this.flushEvents();
            }
        }
    }

    // Destroy analytics instance
    destroy() {
        if (this.flushInterval) {
            clearInterval(this.flushInterval);
        }
        this.flush();
        this.isInitialized = false;
        this.log('Analytics tracking stopped');
    }
}

// Global instance
window.punjabAnalytics = null;

// Initialize analytics when script loads
function initPunjabAnalytics(options = {}) {
    if (!window.punjabAnalytics) {
        window.punjabAnalytics = new PunjabRozgarAnalytics(options);
    }
    return window.punjabAnalytics;
}

// Convenience methods for easy tracking
window.trackEvent = function(eventName, properties = {}) {
    if (window.punjabAnalytics) {
        window.punjabAnalytics.track(eventName, properties);
    }
};

window.trackJobView = function(jobId, jobTitle = '') {
    if (window.punjabAnalytics) {
        window.punjabAnalytics.trackJobInteraction(jobId, 'view', { job_title: jobTitle });
    }
};

window.trackJobApply = function(jobId, jobTitle = '') {
    if (window.punjabAnalytics) {
        window.punjabAnalytics.trackJobInteraction(jobId, 'apply', { job_title: jobTitle });
    }
};

window.trackSearch = function(query, results = 0, filters = {}) {
    if (window.punjabAnalytics) {
        window.punjabAnalytics.trackSearch(query, results, filters);
    }
};

// Auto-initialize with debug mode in development
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    initPunjabAnalytics({ debug: true });
} else {
    initPunjabAnalytics();
}