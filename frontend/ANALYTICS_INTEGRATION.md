# Punjab Rozgar Analytics Integration Guide

## Quick Start

### 1. Add Analytics Script to Your Pages

Add this to the `<head>` section of your HTML pages:

```html
<!-- Punjab Rozgar Analytics Library -->
<script src="js/punjab-analytics.js"></script>
```

### 2. Basic Integration

The analytics will automatically track:
- ✅ Page views
- ✅ Button clicks  
- ✅ Link clicks
- ✅ Form submissions
- ✅ Scroll depth
- ✅ Time on page
- ✅ User sessions

### 3. Job-Specific Tracking

For job listings, add these attributes to your job cards:

```html
<div class="job-card" data-job-id="job_123" data-job-title="Software Developer">
    <!-- Job content -->
    <button onclick="trackJobApply('job_123', 'Software Developer')">Apply</button>
</div>
```

### 4. Custom Event Tracking

Track custom events anywhere in your code:

```javascript
// Track any custom event
trackEvent('Newsletter Signup', {
    source: 'footer',
    email_provided: true
});

// Track job interactions
trackJobView('job_123', 'Software Developer');
trackJobApply('job_123', 'Software Developer');

// Track search queries
trackSearch('software developer', 25, {
    location: 'lahore',
    salary_range: '50k-80k'
});
```

## Integration Examples

### Login/Registration Pages

```html
<form id="login-form">
    <!-- form fields -->
    <button type="submit">Login</button>
</form>

<script>
document.getElementById('login-form').addEventListener('submit', function(e) {
    // Track login attempt
    trackEvent('Login Attempt', {
        method: 'email',
        page: 'login'
    });
});

// Track successful login (call this after successful login)
function onLoginSuccess(userId) {
    trackEvent('Login Success', {
        user_id: userId,
        method: 'email'
    });
}
</script>
```

### Job Search Pages

```html
<form id="search-form">
    <input type="text" id="search-query" placeholder="Search jobs...">
    <select id="location">
        <option value="lahore">Lahore</option>
        <option value="karachi">Karachi</option>
    </select>
    <button type="submit">Search</button>
</form>

<script>
document.getElementById('search-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const query = document.getElementById('search-query').value;
    const location = document.getElementById('location').value;
    
    // Track search
    trackSearch(query, 0, { location: location });
    
    // Perform search and track results
    performSearch(query, location).then(results => {
        trackSearch(query, results.length, { location: location });
    });
});
</script>
```

### Job Detail Pages

```html
<div class="job-detail" data-job-id="job_123">
    <h1>Software Developer</h1>
    <button id="apply-btn">Apply for this Job</button>
    <button id="save-btn">Save Job</button>
</div>

<script>
// Track job view
const jobId = document.querySelector('.job-detail').dataset.jobId;
trackJobView(jobId, document.querySelector('h1').textContent);

// Track application
document.getElementById('apply-btn').addEventListener('click', function() {
    trackJobApply(jobId, 'Software Developer');
});

// Track save
document.getElementById('save-btn').addEventListener('click', function() {
    trackEvent('Job Saved', {
        job_id: jobId,
        source: 'job_detail'
    });
});
</script>
```

### Profile Pages

```html
<form id="profile-form">
    <!-- profile fields -->
    <button type="submit">Update Profile</button>
</form>

<script>
// Track profile views
trackEvent('Profile Page Viewed', {
    section: 'personal_info'
});

// Track profile updates
document.getElementById('profile-form').addEventListener('submit', function(e) {
    trackEvent('Profile Updated', {
        section: 'personal_info',
        fields_updated: ['name', 'email', 'phone']
    });
});
</script>
```

## Available Tracking Methods

| Method | Description | Example |
|--------|-------------|---------|
| `trackEvent(name, properties)` | Track any custom event | `trackEvent('Button Click', {button: 'subscribe'})` |
| `trackJobView(jobId, jobTitle)` | Track job views | `trackJobView('job_123', 'Developer')` |
| `trackJobApply(jobId, jobTitle)` | Track job applications | `trackJobApply('job_123', 'Developer')` |
| `trackSearch(query, results, filters)` | Track search queries | `trackSearch('developer', 25, {location: 'lahore'})` |

## Backend Analytics Dashboard

View your analytics data at:
- **Real-time Dashboard**: `http://localhost:8000/api/v1/analytics/dashboard`
- **All Events**: `http://localhost:8000/api/v1/analytics/events`
- **API Documentation**: `http://localhost:8000/api/docs`

## Configuration

### Debug Mode

Enable debug mode for development:

```javascript
// Manual initialization with debug
initPunjabAnalytics({
    debug: true,
    apiUrl: 'http://localhost:8000/api/v1'
});
```

### Production Setup

For production, update the API URL:

```javascript
initPunjabAnalytics({
    debug: false,
    apiUrl: 'https://your-domain.com/api/v1'
});
```

## Next Steps

1. ✅ Add the analytics script to your base template
2. ✅ Add job tracking attributes to job listings
3. ✅ Test the integration on localhost
4. ✅ Check analytics data in the backend dashboard
5. ✅ Customize tracking for your specific needs

## Support

The analytics system automatically handles:
- ✅ Offline event queuing
- ✅ Batch sending for performance
- ✅ Error handling and retries
- ✅ User privacy (no sensitive data)
- ✅ Cross-browser compatibility