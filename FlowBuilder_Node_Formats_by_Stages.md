# FlowBuilder Node Formats by Implementation Stages

This document categorizes FlowBuilder node types into logical implementation stages based on complexity, usage frequency, and development dependencies.

---

## 📋 Table of Contents
- [Stage 1: Core Foundation Nodes](#stage-1-core-foundation-nodes)
- [Stage 2: Basic Control Flow](#stage-2-basic-control-flow)
- [Stage 3: Advanced Messaging](#stage-3-advanced-messaging)
- [Stage 4: E-commerce Integration](#stage-4-e-commerce-integration)
- [Stage 5: Analytics & Optimization](#stage-5-analytics--optimization)
- [Stage 6: Enterprise Features](#stage-6-enterprise-features)

---

## 🚀 Stage 1: Core Foundation Nodes

**Purpose**: Essential building blocks for any campaign flow. These are the most frequently used nodes and form the foundation of all campaigns.

### 1. MESSAGE Node
**Usage**: Primary communication with customers
**Frequency**: ⭐⭐⭐⭐⭐ (Most Common)

```json
{
  "id": "unique-id",
  "type": "message",
  "content": "Main message text content", // REQUIRED - Primary display field
  "text": "Main message text content",    // Same as content (backward compatibility)
  "label": "Optional label for this message step",
  "addImage": false,
  "imageUrl": "https://example.com/image.jpg", // Only when addImage = true
  "sendContactCard": false,
  "discountType": "none", // "none" | "percentage" | "amount" | "code"
  "discountValue": "",    // Only when discountType != "none"
  "discountCode": "",     // Only when discountType = "code"
  "discountEmail": "",    // Optional email restriction
  "discountExpiry": "",   // Optional expiry date: "2024-12-31T23:59:59"
  "handled": false,
  "aiGenerated": false,
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "reply", // "reply" | "noreply" | "default"
      "intent": "yes", // Only for type="reply"
      "nextStepID": "next-node-id",
      "description": "Optional description for better intent matching",
      "active": true,
      "parameters": {}
    }
  ]
}
```

**Variables**: `{{brand_name}}`, `{{store_url}}`, `{{first_name}}`, `{{customer_timezone}}`, `{{agent_name}}`, `{{opt_in_terms}}`

### 2. END Node
**Usage**: Campaign termination point
**Frequency**: ⭐⭐⭐⭐⭐ (Required for all campaigns)

```json
{
  "id": "unique-id",
  "type": "end",
  "label": "End",
  "active": true,
  "parameters": {},
  "events": [] // End node has no events
}
```

---

## 🎯 Stage 2: Basic Control Flow

**Purpose**: Direct campaign flow and timing controls. Essential for multi-step campaigns.

### 3. DELAY Node
**Usage**: Time-based delays between steps
**Frequency**: ⭐⭐⭐⭐ (Very Common)

```json
{
  "id": "unique-id",
  "type": "delay",
  "time": "5",        // Required - delay value as a string
  "period": "Minutes",// Required - "Seconds" | "Minutes" | "Hours" | "Days"
  "delay": {
    "value": "5",
    "unit": "Minutes"
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 4. SPLIT Node
**Usage**: Branch campaign flow based on conditions
**Frequency**: ⭐⭐⭐ (Common)

```json
{
  "id": "unique-id",
  "type": "split",
  "enabled": true,
  "label": "include",     // Required - split condition label
  "action": "include",    // Split action
  "description": "Optional description of split condition",
  "content": "Display content: include",
  "splitConfig": {
    // Split configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 5. REPLY Node
**Usage**: Handle specific customer responses
**Frequency**: ⭐⭐⭐ (Common)

```json
{
  "id": "unique-id",
  "type": "reply",
  "enabled": true,
  "intent": "yes", // Required - intent name to trigger
  "description": "Optional description of the intent for better context",
  "label": "yes", // Display label (usually same as intent)
  "replyConfig": {
    // Reply configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 6. NO_REPLY Node
**Usage**: Handle customer inactivity
**Frequency**: ⭐⭐⭐ (Common)

```json
{
  "id": "unique-id",
  "type": "no_reply",
  "enabled": true,
  "value": 6,       // Required - wait time as a number
  "unit": "hours",  // Required - "seconds" | "minutes" | "hours" | "days"
  "label": "No Reply",
  "content": "Display content: 6 hours",
  "after": {
    "value": 6,
    "unit": "hours"
  },
  "seconds": 21600, // 6 hours in seconds
  "period": "Hours",
  "noReplyConfig": {
    // No-reply configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

---

## 🔍 Stage 3: Advanced Targeting

**Purpose**: Customer segmentation and personalization features.

### 7. SEGMENT Node
**Usage**: Route customers based on behavior or properties
**Frequency**: ⭐⭐⭐ (Common for targeted campaigns)

```json
{
  "id": "unique-id",
  "type": "segment",
  "label": "Optional label for this segment step",
  "conditions": [
    {
      "id": 1,
      "type": "event", // "event" | "property" | "refill"
      "operator": "has", // "has" | "has_not"
      "action": "placed_order", // "placed_order" | "clicked_link" | "viewed_product" | "added_product_to_cart" | "started_checkout"
      "filter": "all orders",   // "all orders" | "all clicks" | "all product views" | "all cart updates" | "all checkout updates"
      "propertyName": "customer_type",        // Only for type="property"
      "propertyValue": "vip",                 // Only for type="property"
      "propertyOperator": "with a value of",  // "that exists" | "does not exist" | "with a value of" | "with a value not equal to" | "with a value containing" | "with a value not containing"
      "showPropertyValueInput": false,        // Only for type="property"
      "showPropertyOperatorOptions": false,   // Only for type="property"
      "timePeriod": "within the last 30 Days",
      "timePeriodType": "relative",
      "customTimeValue": "7",   // Only when timePeriod is not the default
      "customTimeUnit": "Days", // "Minutes" | "Hours" | "Days"
      "showTimePeriodOptions": false,
      "filterTab": "productId",
      "cartFilterTab": "productId",
      "optInFilterTab": "keywords",
      "showFilterOptions": false,
      "showLinkFilterOptions": false,
      "showCartFilterOptions": false,
      "showOptInFilterOptions": false,
      "filterData": null
    }
  ],
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-yes",
      "type": "split",
      "label": "include",
      "action": "include",
      "nextStepID": "yes-branch-id",
      "active": true,
      "parameters": {}
    },
    {
      "id": "event-no",
      "type": "split",
      "label": "exclude",
      "action": "exclude",
      "nextStepID": "no-branch-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 8. PROPERTY Node
**Usage**: Set or update customer properties
**Frequency**: ⭐⭐ (Less Common)

```json
{
  "id": "unique-id",
  "type": "property",
  "label": "Customer Property Step",
  "content": "Display content: Customer Property Step",
  "properties": [
    {
      "id": 1,
      "name": "customer_type", // Required property name
      "value": "vip"           // Required property value
    }
  ],
  "propertyConfig": {
    // Property configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

---

## 🛒 Stage 4: E-commerce Integration

**Purpose**: Shopping and purchase functionality for retail campaigns.

### 9. PRODUCT_CHOICE Node
**Usage**: Let customers select products to purchase
**Frequency**: ⭐⭐⭐ (Common for retail campaigns)

```json
{
  "id": "unique-id",
  "type": "product_choice",
  "label": "Optional label for product choice step",
  "messageType": "standard", // "standard" | "personalized"
  "messageText": "Reply to buy:\n\nProduct List", // Required message text
  "text": "Reply to buy:\n\nProduct List",        // Backward compatibility
  "prompt": "Which product would you like to purchase?", // Alternative to messageText
  "productSelection": "manually", // "automatically" | "popularity" | "recently_viewed" | "manually"
  "productSelectionPrompt": "Show me products you think I'll like based on my prior purchase, cart, browse behavior, profile properties, and recent messages. If you don't have enough information, show me popular products.",
  "products": [
    {
      "id": "prod-123",          // Required product ID
      "label": "Premium Headphones", // Optional product label
      "showLabel": true,         // Whether to show label
      "uniqueId": 1              // Internal tracking ID
    }
  ],
  "productImages": true,     // Send product images
  "customTotals": false,     // Add custom totals
  "customTotalsAmount": "Shipping", // Custom shipping amount
  "discountExpiry": false,   // Discount has expiry
  "discountExpiryDate": "2024-12-31T23:59:59", // Expiry date when enabled
  "discount": "None",        // Discount type: "None" | "10%" | "$5" | "SAVE20"
  "productChoiceConfig": {
    // Product choice configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-buy",
      "type": "reply",
      "intent": "buy",
      "nextStepID": "purchase-step-id",
      "active": true,
      "parameters": {}
    },
    {
      "id": "event-noreply",
      "type": "noreply",
      "after": {
        "value": 2,
        "unit": "hours"
      },
      "nextStepID": "followup-step-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

**Variables**: `{{Product List}}`, `{{Product List Without Prices}}`, `{{Discount Label}}`, plus message variables

### 10. PURCHASE_OFFER Node
**Usage**: Send targeted purchase offers
**Frequency**: ⭐⭐ (Common for promotional campaigns)

```json
{
  "id": "unique-id",
  "type": "purchase_offer",
  "label": "Optional label for purchase offer step",
  "content": "Display content from label",
  "messageType": "standard",        // "standard" | "personalized"
  "messageText": "Reply 'yes' to buy:\n\nCart List", // Required message text
  "text": "Reply 'yes' to buy:\n\nCart List",        // Backward compatibility
  "cartSource": "manual", // "manual" | "latest"
  "products": [
    {
      "productVariantId": "123123", // Required product variant ID
      "quantity": "3",              // Required quantity as a string
      "uniqueId": 1                 // Internal tracking ID
    }
  ],
  "discount": false,            // Enable/disable discount
  "discountType": "percentage", // "percentage" | "amount" | "code" (only when discount = true)
  "discountPercentage": "",     // Only when discountType = "percentage"
  "discountAmount": "",         // Only when discountType = "amount"
  "discountCode": "",           // Only when discountType = "code"
  "discountAmountLabel": "",    // Optional label for discount code
  "discountEmail": "",          // Optional email restriction
  "discountExpiry": false,      // Discount has expiry
  "discountExpiryDate": "2024-12-31T23:59:59", // Expiry date when enabled
  "customTotals": false,      // Add custom totals
  "shippingAmount": "",       // Custom shipping amount (only when customTotals = true)
  "includeProductImage": true,// Send product images
  "skipForRecentOrders": true,// Skip for recent orders
  "purchaseOfferConfig": {
    // Purchase offer configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-buy",
      "type": "reply",
      "intent": "yes",
      "nextStepID": "purchase-process-id",
      "active": true,
      "parameters": {}
    },
    {
      "id": "event-noreply",
      "type": "noreply",
      "after": {
        "value": 2,
        "unit": "hours"
      },
      "nextStepID": "followup-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

**Variables**: `{{Brand Name}}`, `{{First Name}}`, `{{Discount Label}}`, `{{Cart List}}`, `{{Purchase Link}}`, `{{Agent Name}}`

### 11. PURCHASE Node
**Usage**: Direct purchase processing
**Frequency**: ⭐⭐ (Common for conversion campaigns)

```json
{
  "id": "unique-id",
  "type": "purchase",
  "cartSource": "manual", // "manual" | "latest" - Required
  "products": [
    {
      "productVariantId": "prod-123", // Required product variant ID
      "quantity": "1",                // Required quantity as a string
      "uniqueId": 1                   // Internal tracking ID
    }
  ],
  "discount": false,                 // Add discount to order
  "customTotals": false,             // Add custom totals
  "shippingAmount": "",              // Custom shipping amount (only when customTotals = true)
  "sendReminderForNonPurchasers": false, // Send reminder for non-purchasers
  "allowAutomaticPayment": false,    // Allow automatic payment completion
  "purchaseConfig": {
    // Purchase configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

---

## ⏱️ Stage 5: Campaign Management

**Purpose**: Advanced timing, rate limiting, and scheduling controls.

### 12. SCHEDULE Node
**Usage**: Time-based campaign scheduling
**Frequency**: ⭐⭐ (Common for scheduled campaigns)

```json
{
  "id": "unique-id",
  "type": "schedule",
  "label": "Schedule configuration label",
  "content": "Display content (usually same as label)",
  "schedule": {
    // Schedule configuration object (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-default",
      "type": "split",
      "label": "All other time",
      "nextStepID": "default-branch-id",
      "active": true,
      "parameters": {}
    },
    {
      "id": "event-scheduled",
      "type": "split",
      "label": "Oct 23, 12:00 AM - Oct 30, 12:00 AM",
      "nextStepID": "scheduled-branch-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 13. RATE_LIMIT Node
**Usage**: Control message frequency
**Frequency**: ⭐ (Less Common)

```json
{
  "id": "unique-id",
  "type": "rate_limit",
  "occurrences": "12", // Required - number as a string
  "timespan": "11",    // Required - timespan as a string
  "period": "Minutes", // Required - "Minutes" | "Hours" | "Days"
  "rateLimit": {
    "limit": "12",
    "period": "Minutes"
  },
  "content": "Display content: 12 times every 11 minutes",
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 14. LIMIT Node
**Usage**: Campaign execution limits
**Frequency**: ⭐ (Less Common)

```json
{
  "id": "unique-id",
  "type": "limit",
  "occurrences": "5", // Required - number of occurrences as a string
  "timespan": "1",    // Required - timespan as a string
  "period": "Hours",  // Required - "Minutes" | "Hours" | "Days"
  "limit": {
    "value": "5",
    "period": "Hours"
  },
  "content": "Display content: 5 times every 1 hour",
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

---

## 🧪 Stage 6: Enterprise Features

**Purpose**: Advanced testing, experimentation, and specialized functionality.

### 15. EXPERIMENT Node
**Usage**: A/B testing and campaign experiments
**Frequency**: ⭐ (Enterprise/Advanced)

```json
{
  "id": "unique-id",
  "type": "experiment",
  "label": "Optional label for experiment step",
  "experimentName": "Welcome Message Test", // Required
  "version": "1",
  "content": "Display content: Welcome Message Test(v1)",
  "experimentConfig": {
    // Experiment configuration (handled by the backend)
  },
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-group-a",
      "type": "split",
      "label": "Group A",
      "nextStepID": "group-a-branch-id",
      "active": true,
      "parameters": {}
    },
    {
      "id": "event-group-b",
      "type": "split",
      "label": "Group B",
      "nextStepID": "group-b-branch-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 16. SPLIT_GROUP Node (Experiment Branch)
**Usage**: Generated automatically by EXPERIMENT nodes
**Frequency**: ⭐ (Generated)

```json
{
  "id": "unique-id",
  "type": "split_group",
  "enabled": true,
  "label": "Group A", // Required – typically "Group A" or "Group B"
  "action": "include", // Split action
  "content": "Display content: Group A",
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

### 17. SPLIT_RANGE Node (Schedule Branch)
**Usage**: Generated automatically by SCHEDULE nodes
**Frequency**: ⭐ (Generated)

```json
{
  "id": "unique-id",
  "type": "split_range",
  "enabled": true,
  "label": "Oct 23, 12:00 AM - Oct 30, 12:00 AM", // Required time range
  "action": "include", // Split action
  "content": "Display content: Oct 23, 12:00 AM - Oct 30, 12:00 AM",
  "active": true,
  "parameters": {},
  "events": [
    {
      "id": "event-id",
      "type": "default",
      "nextStepID": "next-node-id",
      "active": true,
      "parameters": {}
    }
  ]
}
```

---

## 📊 Implementation Priority Guide

### **Phase 1: Minimum Viable Product (MVP)**
- **Required Nodes**: MESSAGE, END, DELAY, SPLIT
- **Timeline**: 2-3 weeks
- **Capability**: Basic multi-step campaigns

### **Phase 2: Interactive Campaigns**
- **Add Nodes**: REPLY, NO_REPLY, SEGMENT
- **Timeline**: 1-2 weeks
- **Capability**: Customer interaction and basic targeting

### **Phase 3: E-commerce Integration**
- **Add Nodes**: PRODUCT_CHOICE, PURCHASE_OFFER, PURCHASE
- **Timeline**: 3-4 weeks
- **Capability**: Complete shopping experience

### **Phase 4: Advanced Campaign Management**
- **Add Nodes**: SCHEDULE, PROPERTY, RATE_LIMIT, LIMIT
- **Timeline**: 2-3 weeks
- **Capability**: Professional campaign management

### **Phase 5: Enterprise Features**
- **Add Nodes**: EXPERIMENT, SPLIT_GROUP, SPLIT_RANGE
- **Timeline**: 2-3 weeks
- **Capability**: A/B testing and advanced experimentation

---

## 🔧 Important Implementation Notes

### **General Rules**
1. **ID Generation**: Every node and event must have a unique ID
2. **Event Types**:
   - `default`: Direct connection
   - `reply`: Requires `intent` and `description`
   - `noreply`: Requires an `after` object
   - `split`: Requires `label` and `action`
3. **Backward Compatibility**: Both legacy and new formats are supported
4. **Active Status**: Default is `true` for all nodes and events
5. **Parameters**: Always include an empty object if there are no custom parameters

### **Generated Nodes**
- `SPLIT_GROUP` and `SPLIT_RANGE` are automatically generated by EXPERIMENT and SCHEDULE nodes
- Do not manually create these nodes in campaign JSON

### **Best Practices**
- Start with Stage 1 nodes for all campaigns
- Add Stage 2-3 nodes based on campaign complexity
- Use Stage 4-5 nodes for advanced use cases
- Test node compatibility when combining different stages

---

## 📚 Reference Documentation

- **Complete JSON Structure**: See `format_json_flowbuilder.md` for detailed examples
- **Variable Reference**: Each node type lists available template variables
- **Event Configuration**: Events define how nodes connect and trigger
- **Configuration Objects**: Backend-handled configurations are marked in comments

*Last Updated: October 2025*