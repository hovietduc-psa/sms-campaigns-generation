# SMS Campaign Generation System - User Guide

## Overview

The SMS Campaign Generation System is an AI-powered platform that transforms natural language campaign descriptions into automated SMS campaign flows. This guide will help you get started with creating, managing, and optimizing your SMS campaigns.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Campaign Creation](#campaign-creation)
3. [Campaign Management](#campaign-management)
4. [Advanced Features](#advanced-features)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

## Getting Started

### System Requirements

- Modern web browser (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- Stable internet connection
- Valid API credentials

### Initial Setup

1. **Access the Dashboard**
   - Navigate to your organization's SMS Campaign System URL
   - Log in with your credentials
   - Complete the two-factor authentication if enabled

2. **Account Configuration**
   - Set up your profile information
   - Configure notification preferences
   - Verify your phone number for testing

3. **LLM Provider Configuration**
   - Choose your LLM provider: OpenAI or OpenRouter
   - Configure the appropriate API key in your environment
   - Select your preferred model (see [OpenRouter Integration Guide](OPENROUTER_INTEGRATION.md))

4. **API Key Setup**
   - Generate your API key from the settings page
   - Store it securely for programmatic access
   - Note your rate limits and quotas

### First Campaign

Let's create your first campaign in just a few minutes:

1. Click "Create New Campaign"
2. Enter a simple description like: "Send a welcome message to new subscribers"
3. Click "Generate Campaign"
4. Review the generated flow
5. Test the campaign with a sample phone number
6. Launch your campaign!

## Campaign Creation

### Understanding Campaign Descriptions

The system uses natural language processing to understand your campaign requirements. Here's how to write effective descriptions:

#### Simple Campaigns
```
"Send a welcome message to new subscribers"
"Create a weekly promotional campaign"
"Send birthday wishes to customers"
```

#### Complex Campaigns
```
"Create an abandoned cart recovery campaign with 3 messages:
1. First message 2 hours after cart abandonment with 10% discount
2. Second message 24 hours later with free shipping offer
3. Final message 72 hours later with urgency messaging"
```

#### Multi-branch Campaigns
```
"Create a customer segmentation campaign:
- Premium customers get exclusive offers and early access
- Regular customers get standard promotions
- New customers get a welcome series with educational content"
```

### Campaign Parameters

When creating campaigns, you can specify:

#### Timing Parameters
- **Immediate**: Send right away
- **Delays**: Wait specific time periods
- **Scheduled**: Send at specific dates/times
- **Conditional**: Send based on user actions

#### Personalization
- **Dynamic Content**: Use customer data in messages
- **Conditional Logic**: Different messages based on user attributes
- **A/B Testing**: Test different message variations

#### Compliance
- **Time Zones**: Respect local time zones
- **Consent Management**: Honor opt-out preferences
- **Frequency Limits**: Avoid message fatigue

### Step-by-Step Campaign Creation

#### Step 1: Define Your Goal
What do you want to achieve?
- Welcome new users
- Promote products
- Recover abandoned carts
- Re-engage inactive users

#### Step 2: Write Your Description
Be specific about:
- Target audience
- Message timing
- Personalization elements
- Success criteria

#### Step 3: Generate Campaign
Click "Generate Campaign" and let the AI create your flow.

#### Step 4: Review and Customize
- Review the generated steps
- Modify message content
- Adjust timing
- Add conditional logic

#### Step 5: Test Campaign
- Send test messages to verified numbers
- Check message formatting
- Verify timing logic
- Test all branches

#### Step 6: Launch Campaign
- Set launch parameters
- Define audience segments
- Configure delivery settings
- Monitor initial results

## Campaign Management

### Dashboard Overview

Your dashboard provides:

#### Campaign Metrics
- **Active Campaigns**: Currently running campaigns
- **Completion Rates**: Success rates for campaigns
- **Response Rates**: Customer engagement metrics
- **ROI Analysis**: Campaign performance analytics

#### Real-time Monitoring
- **Delivery Status**: Real-time message delivery tracking
- **Error Tracking**: Failed deliveries and reasons
- **Performance Metrics**: Response times and system health

### Campaign Types

#### Welcome Campaigns
**Purpose**: Onboard new subscribers
**Best Practices**:
- Send immediately after opt-in
- Include company introduction
- Set expectations for message frequency
- Provide value in first message

#### Promotional Campaigns
**Purpose**: Drive sales and engagement
**Best Practices**:
- Clear call-to-action
- Time-sensitive offers
- Personalized recommendations
- Compliance with regulations

#### Re-engagement Campaigns
**Purpose**: Reactivate inactive users
**Best Practices**:
- Analyze inactivity reasons
- Offer incentives to return
- Update customer preferences
- Respect opt-out requests

#### Educational Campaigns
**Purpose**: Inform and educate customers
**Best Practices**:
- Break content into digestible parts
- Include practical examples
- Provide additional resources
- Encourage interaction

### Audience Management

#### Segmentation
Create targeted audiences based on:
- **Demographics**: Age, location, gender
- **Behavior**: Purchase history, engagement
- **Preferences**: Product interests, communication frequency
- **Lifecycle**: New, active, at-risk, churned

#### Dynamic Segments
Automatically update segments based on:
- Recent purchases
- Website activity
- Email engagement
- SMS responses

#### Consent Management
- Track opt-in sources
- Honor opt-out requests
- Maintain preference history
- Comply with regulations

### Message Management

#### Content Creation
- **Keep it concise**: 160 characters or less
- **Personalize**: Use customer data appropriately
- **Clear CTA**: Tell customers what to do next
- **Brand Voice**: Maintain consistent tone

#### Template Library
- Save common message templates
- Include personalization placeholders
- Organize by campaign type
- A/B test different versions

#### Compliance Checklist
- [ ] Opt-in consent documented
- [ ] Company name included
- [ ] Opt-out instructions provided
- [ ] Time zone compliance checked
- [ ] Frequency limits respected

## Advanced Features

### A/B Testing

#### Test Variables
- **Message Content**: Different wording or offers
- **Timing**: Different send times or delays
- **Calls to Action**: Different response mechanisms
- **Personalization**: Different data points used

#### Test Setup
1. Create campaign variations
2. Define test audience segments
3. Set success metrics
4. Launch test
5. Monitor results
6. Implement winner

#### Statistical Significance
- Ensure adequate sample size
- Run tests for sufficient duration
- Use statistical tools for analysis
- Consider seasonal variations

### Automation Rules

#### Triggers
- **User Actions**: Purchases, website visits, form submissions
- **Time-based**: Birthdays, anniversaries, inactivity
- **Behavioral**: Cart abandonment, browsing patterns
- **External**: API calls, webhooks

#### Conditions
- **If/Then Logic**: Simple conditional branching
- **Complex Logic**: Multiple conditions and operators
- **Data Validation**: Ensure data quality
- **Fallback Options**: Handle edge cases

#### Actions
- **Send Messages**: SMS, email, push notifications
- **Update Data**: Modify customer records
- **Integrate**: Call external APIs
- **Notify**: Alert team members

### Integration Capabilities

#### CRM Integration
- **Data Sync**: Customer data synchronization
- **Campaign Triggers**: CRM events initiate campaigns
- **Result Tracking**: Update CRM with campaign results
- **Segmentation**: Use CRM data for targeting

#### E-commerce Integration
- **Cart Recovery**: Abandoned cart campaigns
- **Purchase Follow-up**: Post-purchase sequences
- **Product Recommendations**: AI-powered suggestions
- **Inventory Sync**: Real-time stock updates

#### Analytics Integration
- **Data Collection**: Campaign performance metrics
- **Conversion Tracking**: End-to-end attribution
- **Customer Journey**: Multi-channel analysis
- **ROI Calculation**: Revenue impact measurement

### Custom Workflows

#### Workflow Builder
Create complex multi-step campaigns:
- **Parallel Paths**: Simultaneous message sequences
- **Wait Steps**: Time-based delays
- **Decision Points**: Conditional branching
- **Integration Points**: External service calls

#### Error Handling
- **Retry Logic**: Automatic retry on failures
- **Fallback Paths**: Alternative message delivery
- **Error Notifications**: Alert team on issues
- **Dead Letter Queue**: Handle failed messages

## Best Practices

### Campaign Design

#### Customer Experience
- **Value First**: Provide value in every message
- **Respect Time**: Send at appropriate hours
- **Personalization**: Use customer data thoughtfully
- **Clarity**: Clear, concise messaging

#### Technical Implementation
- **Mobile-First**: Optimize for mobile devices
- **Compliance**: Follow all regulations
- **Testing**: Thoroughly test all scenarios
- **Monitoring**: Track performance metrics

### Content Strategy

#### Message Content
- **Brand Voice**: Maintain consistent tone
- **Personalization**: Use customer names and data
- **Clarity**: Clear, actionable messages
- **Brevity**: Keep messages concise

#### Timing Strategy
- **Optimal Times**: Send when customers are likely to engage
- **Frequency**: Don't overwhelm customers
- **Sequencing**: Logical message flow
- **Time Zones**: Respect local times

### Performance Optimization

#### Key Metrics
- **Delivery Rate**: Messages successfully delivered
- **Open Rate**: Messages read by recipients
- **Click-Through Rate**: Links clicked in messages
- **Conversion Rate**: Desired actions completed

#### Continuous Improvement
- **A/B Testing**: Continuously test variations
- **Analytics**: Regular performance review
- **Customer Feedback**: Listen to customer responses
- **Competitor Analysis**: Monitor industry trends

### Security and Compliance

#### Data Protection
- **Encryption**: Secure data transmission
- **Access Control**: Limit data access
- **Audit Logs**: Track all activities
- **Data Retention**: Follow data retention policies

#### Regulatory Compliance
- **GDPR**: European data protection
- **TCPA**: US telemarketing regulations
- **CASL**: Canadian anti-spam legislation
- **Local Laws**: Region-specific requirements

## Troubleshooting

### Common Issues

#### Campaign Not Sending
1. **Check API Keys**: Verify credentials are valid
2. **Review Content**: Ensure messages comply with regulations
3. **Check Balance**: Verify sufficient credits/quotas
4. **Review Logs**: Check for error messages

#### Low Response Rates
1. **Message Content**: Review message relevance and clarity
2. **Timing**: Check send times and frequency
3. **Audience**: Verify target audience appropriateness
4. **Calls to Action**: Ensure clear, compelling CTAs

#### Delivery Failures
1. **Phone Numbers**: Verify number format and validity
2. **Carrier Issues**: Check with SMS provider
3. **Content Filtering**: Review message for restricted content
4. **Rate Limits**: Ensure compliance with sending limits

#### Technical Issues
1. **API Connectivity**: Check network connectivity
2. **System Status**: Verify system health
3. **Browser Issues**: Try different browser or clear cache
4. **Support Contact**: Reach out for technical assistance

### Support Resources

#### Self-Service
- **Knowledge Base**: Comprehensive documentation
- **Video Tutorials**: Step-by-step guides
- **FAQ Section**: Common questions and answers
- **Community Forum**: User discussions and solutions

#### Direct Support
- **Email Support**: support@yourcompany.com
- **Phone Support**: 1-800-SUPPORT
- **Live Chat**: Available on website
- **Priority Support**: Enterprise customers

### Getting Help

#### Before Contacting Support
1. **Check Status**: Verify system status page
2. **Review Documentation**: Consult relevant guides
3. **Gather Information**: Collect error messages and details
4. **Reproduce Issue**: Document steps to reproduce

#### Contact Information
- **Support Portal**: https://support.yourcompany.com
- **Email**: support@yourcompany.com
- **Phone**: 1-800-SUPPORT (Mon-Fri, 9 AM - 6 PM EST)
- **Emergency**: emergency@yourcompany.com (critical issues only)

## API Reference

### Authentication

All API requests require authentication using Bearer tokens:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.yourdomain.com/api/v1/generateFlow
```

### Endpoints

#### Generate Campaign Flow
```http
POST /api/v1/generateFlow
Content-Type: application/json

{
  "campaignDescription": "Create a welcome series for new subscribers"
}
```

#### Generate Batch Campaigns
```http
POST /api/v1/generateFlow/batch
Content-Type: application/json

[
  {"campaignDescription": "Welcome campaign"},
  {"campaignDescription": "Promotional campaign"}
]
```

#### Get Campaign Statistics
```http
GET /api/v1/stats
Authorization: Bearer YOUR_API_KEY
```

#### Health Check
```http
GET /api/v1/health
```

### Error Handling

The API returns standard HTTP status codes:

- **200**: Success
- **400**: Bad Request
- **401**: Unauthorized
- **422**: Validation Error
- **429**: Rate Limited
- **500**: Internal Server Error

Error response format:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "correlation_id": "request-tracking-id",
  "status": "error",
  "type": "error_category"
}
```

### Rate Limits

- **Standard**: 100 requests per minute
- **Burst**: Up to 150 requests in a single burst
- **Batch**: Maximum 10 campaigns per batch request
- **Daily**: 10,000 requests per day (adjustable)

Check rate limit headers:
- `X-RateLimit-Limit`: Maximum requests per window
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Time when rate limit resets

### SDKs and Libraries

#### Python
```python
import requests

client = requests.Session()
client.headers.update({
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
})

response = client.post(
    'https://api.yourdomain.com/api/v1/generateFlow',
    json={'campaignDescription': 'Welcome campaign'}
)
```

#### JavaScript
```javascript
const response = await fetch('https://api.yourdomain.com/api/v1/generateFlow', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    campaignDescription: 'Welcome campaign'
  })
});

const result = await response.json();
```

## Conclusion

The SMS Campaign Generation System provides powerful tools for creating sophisticated SMS marketing campaigns. By following this guide and best practices, you can create effective campaigns that drive engagement and results while maintaining compliance and excellent customer experience.

For additional help, refer to our:
- [Knowledge Base](https://support.yourcompany.com/kb)
- [Video Tutorials](https://support.yourcompany.com/tutorials)
- [Community Forum](https://community.yourcompany.com)
- [Support Portal](https://support.yourcompany.com)