# Vercel Web Analytics Integration

## Overview

Vercel Web Analytics has been integrated into the AgentInterOp project to track user interactions and page views across all frontend interfaces. This document describes the integration and usage.

## Implementation

### What is Vercel Web Analytics?

Vercel Web Analytics is a privacy-first analytics tool that provides insights into visitor behavior and page performance without requiring external scripts or complex setup. It automatically:

- Tracks page views
- Measures Core Web Vitals
- Provides visitor information
- Respects user privacy

### Prerequisites

- **Vercel Account**: Required to use Web Analytics
- **Vercel Project**: The project must be deployed on Vercel
- **Enable Web Analytics**: Must be enabled in the Vercel dashboard

### Setup in Vercel Dashboard

1. Go to your [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project (AgentInterOp)
3. Click the **Analytics** tab
4. Click **Enable** to activate Web Analytics
5. After enabling, new routes (scoped at `/_vercel/insights/*`) will be available on your next deployment

**Note**: Enabling Web Analytics will add new routes at `/_vercel/insights/*` after your next deployment.

## Implementation Details

### HTML Templates Enhanced

Web Analytics has been added to the following HTML templates in `app/web/templates/`:

- `demo.html` - Main demo landing page
- `simple_index.html` - Simple interface for multi-agent interactions
- `index.html` - Connectathon demo interface
- `config.html` - Configuration control panel
- `agent_management.html` - Healthcare agent management system
- `agent_studio.html` - Agent studio development platform
- `inspector.html` - A2A inspector tool
- `partner_connect.html` - Partner connect testing interface
- `splash.html` - Splash landing page
- `use_cases.html` - Healthcare AI agent use cases showcase
- `test_harness.html` - Test harness for scripted scenarios

### Integration Method

For plain HTML sites deployed on Vercel, Web Analytics is integrated using the HTML script injection method. The following code has been added to the `<head>` section of each template:

```html
<!-- Vercel Web Analytics -->
<script>
  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
</script>
<script defer src="/_vercel/insights/script.js"></script>
```

This implementation:

1. **Initializes the tracking function**: The first script defines `window.va` as a function that queues events if the analytics script hasn't loaded yet
2. **Defers the analytics script**: The second script is loaded asynchronously with `defer` to not block page rendering
3. **No external dependencies**: Unlike `@vercel/analytics` package, this method requires no npm packages
4. **Privacy-first**: Vercel Web Analytics respects user privacy and doesn't use cookies

### How It Works

- **Automatic page view tracking**: Every page visit is automatically tracked
- **Route detection**: Page routes are automatically extracted from the URL
- **Performance metrics**: Core Web Vitals are collected automatically
- **Request tracking**: Network requests to `/_vercel/insights/view` confirm analytics are working

You should see Fetch/XHR requests to `/_vercel/insights/view` in your browser's Network tab when visiting any page.

## Viewing Analytics

Once deployed to Vercel and with users visiting your site:

1. Go to your project in the [Vercel Dashboard](https://vercel.com/dashboard)
2. Click the **Analytics** tab
3. View your analytics data including:
   - Visitor count
   - Page views
   - Top pages
   - Core Web Vitals
   - Geographic distribution

After a few days of visitors, you'll be able to:

- View detailed analytics panels
- Filter data by various dimensions
- Explore performance metrics

## Advanced Features (Pro/Enterprise)

Users on Vercel's Pro and Enterprise plans can:

- Add custom events to track specific user interactions
- Set up custom dashboards
- Export raw analytics data
- Access more granular filtering options

## No Configuration Required

The HTML script injection method used here:

- ✅ Requires NO configuration
- ✅ Requires NO additional npm packages
- ✅ Works automatically after deployment
- ✅ NO route support (but route tracking is automatic)
- ✅ Respects privacy standards

## Privacy & Compliance

Vercel Web Analytics is designed with privacy in mind:

- No personal data is collected
- No cookies are used
- GDPR and CCPA compliant
- User privacy is respected by default

For more information, see [Vercel Web Analytics Privacy Policy](https://vercel.com/docs/analytics/privacy-policy)

## Next Steps

### Deploy to Vercel

After making these changes:

```bash
git add .
git commit -m "Add Vercel Web Analytics integration"
vercel deploy
```

### Monitor Analytics

Once deployed:

1. Visit your deployed application
2. Navigate through different pages
3. Check the browser's Network tab for requests to `/_vercel/insights/view`
4. After a few minutes, check your Vercel Dashboard Analytics tab

### Custom Events (Pro/Enterprise)

If you're on a Pro or Enterprise plan and want to track specific user interactions:

```javascript
// Track button clicks, form submissions, etc.
window.va('event', { name: 'custom_event_name' });
```

For more details, see [Vercel Web Analytics Custom Events Documentation](https://vercel.com/docs/analytics/custom-events)

## Troubleshooting

### Analytics Not Showing Data

1. **Ensure Web Analytics is enabled**: Check Vercel Dashboard → Analytics → Enable
2. **Wait after deployment**: Data may take a few minutes to appear
3. **Check network requests**: Look for `/_vercel/insights/view` requests in browser Network tab
4. **Verify deployment**: Ensure the app is deployed on Vercel
5. **Check browser privacy settings**: Some privacy extensions may block analytics

### No Requests to `/_vercel/insights/view`

- Verify the script tags are present in your HTML
- Check browser console for any errors
- Ensure JavaScript is enabled
- Check if privacy-blocking extensions are active

## Additional Resources

- [Vercel Web Analytics Documentation](https://vercel.com/docs/analytics)
- [Vercel Analytics Filtering Guide](https://vercel.com/docs/analytics/filtering)
- [Custom Events Documentation](https://vercel.com/docs/analytics/custom-events)
- [Privacy and Compliance](https://vercel.com/docs/analytics/privacy-policy)
- [Pricing and Limits](https://vercel.com/docs/analytics/limits-and-pricing)

## Support

For issues or questions about Vercel Web Analytics:

1. Check [Vercel Documentation](https://vercel.com/docs/analytics)
2. Visit [Vercel Community](https://github.com/vercel/vercel/discussions)
3. Contact Vercel Support through your dashboard
