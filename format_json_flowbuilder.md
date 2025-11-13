# AI Flow Generation Guide - Complete Node Structure Reference

**Comprehensive guide for AI to generate accurate JSON structures for SMS Marketing Campaign Flow based on actual EditDrawer implementations**

## 🎯 Objective

Create documentation to help AI understand and generate correct JSON structure for SMS Marketing Campaign Flow with **all node types, fields, and connection logic** based on actual EditDrawer component implementations.

## 📋 Root JSON Structure

### Root Structure
```json
{
  "name": "string",           // Campaign name (required)
  "description": "string",    // Campaign description (required)
  "initialStepID": "string",  // Starting node ID (required)
  "steps": [...]              // Array of nodes (required)
}
```

### Step Structure (Base) - Applies to ALL nodes
```json
{
  "id": "unique-id",         // Unique identifier (required)
  "type": "node-type",       // Node type (required)
  "label": "Display Label",  // Display label (required)
  "content": "Description",  // Content description (required)
  "active": true,            // Status (optional, default: true)
  "parameters": {},          // Additional parameters (optional)
  "events": []               // Events array (optional)
  // ... node-specific fields
}
```

### Event Structure
```json
{
  "type": "reply|noreply|split|default", // Event type (required)
  "nextStepID": "target-node-id",        // Target node (required)
  "active": true,                         // Event active status (optional)
  "parameters": {},                       // Event parameters (optional)
  // Fields by event type:
  "intent": "string",         // Only for type="reply"
  "description": "string",    // Optional for type="reply"
  "after": {"value": 2, "unit": "hours"}, // Only for type="noreply"
  "label": "string",          // Only for type="split"
  "action": "string"          // Only for type="split"
}
```

## 🚨 IMPORTANT: Unique nextStepID Rules

**Each nextStepID must be UNIQUE throughout the entire flow to avoid conflicts!**

### ✅ CORRECT: Unique IDs
```json
{
  "welcome-001": {
    "events": [
      {"nextStepID": "shop-002"},     // ✅ Unique
      {"nextStepID": "noreply-003"}   // ✅ Unique
    ]
  },
  "shop-002": {
    "events": [
      {"nextStepID": "vip-products-004"}, // ✅ Unique
      {"nextStepID": "regular-products-005"} // ✅ Unique
    ]
  }
}
```

### ❌ WRONG: Duplicate IDs
```json
{
  "welcome-001": {
    "events": [
      {"nextStepID": "shop-002"},
      {"nextStepID": "shop-002"}      // ❌ DUPLICATE!
    ]
  }
}
```

### 🎯 Best Practice: Counter-based IDs
```
welcome-001
shop-002
vip-products-003
purchase-004
noreply-005
end-flow-006
```

## 📦 ALL NODE TYPES AND DETAILED STRUCTURE

### 1. MESSAGE NODE - Send SMS message
```json
{
  "id": "message-001",
  "type": "message",
  "label": "Welcome Message",
  "content": "Send welcome message with discount",
  "messageText": "Hi {{first_name}}! Welcome to {{brand_name}}! Use code WELCOME15 for 15% off",
  "text": "",                        // Backward compatibility (optional)
  "addImage": false,                // Include image (optional)
  "imageUrl": "",                   // Image URL (optional)
  "sendContactCard": false,         // Send contact card (optional)
  "discountType": "percentage",     // "none" | "percentage" | "amount" | "code"
  "discountValue": "15",            // Discount value (for percentage/amount)
  "discountCode": "WELCOME15",      // Discount code (for type="code")
  "discountEmail": "",              // Email restriction for discount
  "discountExpiry": "",             // Discount expiry date
  "handled": false,                 // Processing status (optional)
  "aiGenerated": false              // AI generation status (optional)
}
```

**Available Variables:**
- `{{brand_name}}` - Brand name
- `{{first_name}}` - Customer first name
- `{{last_name}}` - Customer last name
- `{{store_url}}` - Store URL
- `{{customer_timezone}}` - Customer timezone
- `{{agent_name}}` - Agent name
- `{{opt_in_terms}}` - Opt-in terms

### 2. DELAY NODE - Wait time
```json
{
  "id": "delay-001",
  "type": "delay",
  "label": "Wait 2 Hours",
  "content": "Wait before next message",
  "time": "2",
  "period": "Hours",                // "Seconds" | "Minutes" | "Hours" | "Days"
  "delay": {                        // Structured format (optional)
    "value": "2",
    "unit": "Hours"
  }
}
```

### 3. SEGMENT NODE - Customer segmentation
```json
{
  "id": "segment-001",
  "type": "segment",
  "label": "VIP Customer Check",
  "content": "Customer matches 2 conditions",
  "conditions": [
    {
      "id": 1,
      "type": "event",               // "event" | "property" | "refill"
      "action": "placed_order",     // Event type
      "operator": "has",             // "has" | "has_not"
      "filter": "all orders",       // Filter type
      "timePeriod": "within the last 90 days",
      "timePeriodType": "relative",  // "relative" | "absolute"
      "filterTab": "productId",     // Filter tab
      "cartFilterTab": "productId",
      "optInFilterTab": "keywords",
      "showFilterOptions": false,
      "showLinkFilterOptions": false,
      "showCartFilterOptions": false,
      "showOptInFilterOptions": false,
      "filterData": null
    }
  ],
  "segmentDefinition": {}           // Legacy format (optional)
}
```

**Common event types:**
- `placed_order` - Placed an order
- `clicked_link` - Clicked link
- `viewed_product` - Viewed product
- `added_product_to_cart` - Added to cart
- `started_checkout` - Started checkout
- `placed_order_text` - Placed order via SMS
- `opted_into_sms` - Opted into SMS
- `received_outbound` - Received outbound message
- `sent_inbound` - Sent inbound message

### 4. PRODUCT_CHOICE NODE - Product selection
```json
{
  "id": "products-001",
  "type": "product_choice",
  "label": "Product Selection",
  "content": "Show available products",
  "messageType": "standard",         // "standard" | "personalized"
  "messageText": "Choose your product:\n\n{{Product List}}\n\nReply with number!",
  "text": "",                        // Backward compatibility
  "prompt": "",                      // Alternative to messageText
  "productSelection": "manually",    // "manually" | "automatically" | "popularity" | "recently_viewed"
  "productSelectionPrompt": "",      // Prompt for automatic selection
  "products": [
    {
      "id": "prod-001",
      "label": "Premium T-Shirt",
      "showLabel": true,
      "uniqueId": 1
    }
  ],
  "productImages": true,             // Send product images
  "customTotals": false,             // Custom totals
  "customTotalsAmount": "Shipping",  // Custom shipping amount
  "discountExpiry": false,           // Discount has expiry
  "discountExpiryDate": "",          // Expiry date
  "discountType": "percentage",     // "none" | "percentage" | "amount" | "code"
  "discountValue": "10",            // Discount value
  "discountCode": "SAVE10",         // Discount code
  "discountEmail": "",              // Email restriction
  "discount": "None",               // Legacy field (optional)
  "productChoiceConfig": {}         // Configuration (optional)
}
```

**Variables for ProductChoice:**
- `{{Product List}}` - Product list with prices
- `{{Product List Without Prices}}` - Product list without prices
- `{{Discount Label}}` - Discount label
- `{{brand_name}}`, `{{first_name}}`, etc.

### 5. PURCHASE NODE - Process purchase
```json
{
  "id": "purchase-001",
  "type": "purchase",
  "label": "Complete Purchase",
  "content": "Process customer purchase",
  "cartSource": "latest",            // "manual" | "latest"
  "products": [
    {
      "productVariantId": "variant-123",
      "quantity": "1",
      "uniqueId": 1
    }
  ],
  "discountType": "none",           // "none" | "percentage" | "amount" | "code"
  "discountValue": "",              // Discount value (for percentage/amount)
  "discountCode": "",               // Discount code (for type="code")
  "discountEmail": "",              // Email restriction for discount
  "customTotals": false,            // Custom totals
  "shippingAmount": "",            // Shipping fee
  "sendReminderForNonPurchasers": false, // Send reminder
  "allowAutomaticPayment": false,   // Auto payment
  "discount": false,                // Legacy boolean field
  "purchaseConfig": {}              // Purchase configuration (optional)
}
```

### 6. PURCHASE_OFFER NODE - Send purchase offer
```json
{
  "id": "purchase-offer-001",
  "type": "purchase_offer",
  "label": "Special Offer",
  "content": "Send product offer",
  "messageType": "standard",         // "standard" | "personalized"
  "messageText": "Special offer! Check out these products:",
  "text": "",                        // Backward compatibility
  "cartSource": "manual",            // "manual" | "latest"
  "products": [
    {
      "productVariantId": "variant-123",
      "quantity": "1",
      "uniqueId": 1
    }
  ],
  "discount": false,                 // Enable/disable discount
  "discountType": "percentage",      // "none" | "percentage" | "amount" | "code"
  "discountPercentage": "",         // Only for type="percentage"
  "discountAmount": "",             // Only for type="amount"
  "discountCode": "",               // Only for type="code"
  "discountAmountLabel": "",        // Label for code discount
  "discountEmail": "",              // Email restriction
  "discountExpiry": false,          // Discount has expiry
  "discountExpiryDate": "",         // Expiry date
  "customTotals": false,            // Custom totals
  "shippingAmount": "",            // Custom shipping
  "includeProductImage": true,      // Send product image
  "skipForRecentOrders": false,     // Skip for recent orders
  "purchaseOfferConfig": {}         // Configuration (optional)
}
```

### 7. REPLY_CART_CHOICE NODE - Choose from cart
```json
{
  "id": "cart-choice-001",
  "type": "reply_cart_choice",
  "label": "Choose from Cart",
  "content": "Select items from cart",
  "messageType": "standard",         // "standard" | "personalized"
  "messageText": "Choose from your cart:",
  "text": "",                        // Backward compatibility
  "prompt": "",                      // Alternative to messageText
  "cartSelection": "latest",         // "manual" | "latest"
  "cartItems": [
    {
      "id": "cart-001",
      "label": "Item from Cart",
      "showLabel": true,
      "uniqueId": 1
    }
  ],
  "customTotals": false,             // Custom totals
  "customTotalsAmount": "Shipping",  // Custom shipping amount
  "replyCartChoiceConfig": {}        // Configuration (optional)
}
```

### 8. NO_REPLY NODE - Handle no response
```json
{
  "id": "noreply-001",
  "type": "no_reply",
  "label": "No Response Handler",
  "content": "Handle when customer doesn't reply",
  "enabled": true,                   // Enable/disable
  "value": 2,                        // Wait time as number
  "unit": "hours",                   // "seconds" | "minutes" | "hours" | "days"
  "after": {                         // Structured format (optional)
    "value": 2,
    "unit": "hours"
  },
  "seconds": 7200,                  // Wait time in seconds (legacy)
  "period": "Hours",                 // Legacy period
  "noReplyConfig": {}                // Configuration (optional)
}
```

### 9. END NODE - End flow
```json
{
  "id": "end-flow-001",
  "type": "end",
  "label": "Campaign End",
  "content": "End of campaign flow"
}
```

### 10. START NODE - Start flow
```json
{
  "id": "start-001",
  "type": "start",
  "label": "Start",
  "content": "Flow begins here"
}
```

### 11. PROPERTY NODE - Update properties
```json
{
  "id": "property-001",
  "type": "property",
  "label": "Update Customer Properties",
  "content": "Update customer properties",
  "properties": [
    {
      "name": "customer_type",
      "value": "vip",
      "id": "prop_1"
    },
    {
      "name": "last_purchase_date",
      "value": "2024-11-07",
      "id": "prop_2"
    }
  ]
}
```

### 12. RATE_LIMIT NODE - Rate limiting
```json
{
  "id": "rate-limit-001",
  "type": "rate_limit",
  "label": "Rate Limit",
  "content": "Control message frequency",
  "occurrences": "12",              // Number of sends
  "timespan": "1",                  // Time period
  "period": "Hours",                 // "Minutes" | "Hours" | "Days"
  "rateLimit": {                     // Structured format (optional)
    "limit": "12",
    "period": "Hours"
  }
}
```

### 13. LIMIT NODE - Execution limit
```json
{
  "id": "limit-001",
  "type": "limit",
  "label": "Execution Limit",
  "content": "Limit execution count",
  "occurrences": "5",               // Number of times allowed
  "timespan": "1",                  // Time period
  "period": "Hours",                 // "Minutes" | "Hours" | "Days"
  "limit": {                        // Structured format (optional)
    "value": "5",
    "period": "Hours"
  }
}
```

### 14. SPLIT NODE - Split branch
```json
{
  "id": "split-001",
  "type": "split",
  "label": "Split Flow",
  "content": "Split flow based on conditions",
  "enabled": true,                   // Enable/disable
  "action": "include",              // Split action
  "description": "Split description",
  "splitConfig": {}                  // Split configuration (optional)
}
```

### 15. REPLY NODE - Wait for reply
```json
{
  "id": "reply-001",
  "type": "reply",
  "label": "Wait for Reply",
  "content": "Wait for customer response",
  "enabled": true,                   // Enable/disable
  "intent": "yes",                   // Reply intent
  "description": "Wait for yes response",
  "replyConfig": {}                  // Reply configuration (optional)
}
```

### 16. EXPERIMENT NODE - A/B Testing
```json
{
  "id": "experiment-001",
  "type": "experiment",
  "label": "Welcome Message Test",
  "content": "Welcome Message Test (v1)",
  "experimentName": "Welcome Message Test", // Experiment name
  "version": "1"                      // Version
}
```

### 17. QUIZ NODE - Interactive quiz
```json
{
  "id": "quiz-001",
  "type": "quiz",
  "label": "Customer Quiz",
  "content": "Interactive customer quiz",
  "questions": [
    {
      "id": "q1",
      "question": "What type of products do you prefer?",
      "type": "single",                 // "single" | "multiple" | "text"
      "options": ["Electronics", "Clothing", "Food"],
      "correctAnswer": "Electronics",
      "points": 10
    }
  ],
  "quizConfig": {
    "timeLimit": 300,                 // 5 minutes
    "passingScore": 70,
    "shuffleQuestions": false,
    "showResults": true
  }
}
```

### 18. SCHEDULE NODE - Schedule
```json
{
  "id": "schedule-001",
  "type": "schedule",
  "label": "Schedule",
  "content": "Schedule execution time"
}
```

### 19. SPLIT_GROUP NODE - A/B testing branch
```json
{
  "id": "split-group-001",
  "type": "split_group",
  "label": "Group A",
  "content": "Experiment variant group",
  "enabled": true,
  "action": "control",              // "control" | "variant"
  "description": "Control group",
  "splitConfig": {}
}
```

### 20. SPLIT_RANGE NODE - Time-based branch
```json
{
  "id": "split-range-001",
  "type": "split_range",
  "label": "Oct 23, 12:00 AM - Oct 30, 12:00 AM",
  "content": "Time-based flow split",
  "enabled": true,
  "action": "schedule",
  "description": "Scheduled time range",
  "splitConfig": {}
}
```

## 🎪 Common Event Patterns

### 1. Reply + NoReply Pattern
```json
{
  "events": [
    {
      "type": "reply",
      "intent": "yes",
      "nextStepID": "continue-flow-002",
      "description": "Customer wants to continue"
    },
    {
      "type": "noreply",
      "after": {"value": 24, "unit": "hours"},
      "nextStepID": "followup-003",
      "description": "No response after 24 hours"
    }
  ]
}
```

### 2. Split Pattern (A/B Test)
```json
{
  "events": [
    {
      "type": "split",
      "label": "Group A",
      "action": "control",
      "nextStepID": "variant-a-002"
    },
    {
      "type": "split",
      "label": "Group B",
      "action": "variant",
      "nextStepID": "variant-b-003"
    }
  ]
}
```

### 3. Default Pattern (Direct)
```json
{
  "events": [
    {
      "type": "default",
      "nextStepID": "next-step-002"
    }
  ]
}
```

### 4. Product Choice Pattern
```json
{
  "events": [
    {
      "type": "reply",
      "intent": "buy",
      "nextStepID": "purchase-004",
      "description": "Customer wants to buy"
    },
    {
      "type": "reply",
      "intent": "info",
      "nextStepID": "product-info-005",
      "description": "Customer wants more information"
    },
    {
      "type": "noreply",
      "after": {"value": 2, "unit": "hours"},
      "nextStepID": "followup-006",
      "description": "No response after 2 hours"
    }
  ]
}
```

## 🎯 Example: Complete Discount Campaign Flow

When user says: *"Create a 20% discount campaign for new customers with A/B testing"*

### AI should create:

```json
{
  "name": "New Customer Discount Campaign with A/B Testing",
  "description": "Welcome campaign with 20% discount for new customers with A/B testing on message content",
  "initialStepID": "experiment-001",
  "steps": [
    {
      "id": "experiment-001",
      "type": "experiment",
      "label": "Welcome Message Test",
      "content": "Welcome Message Test (v1)",
      "experimentName": "Welcome Message Test",
      "version": "1",
      "events": [
        {
          "type": "split",
          "label": "Group A",
          "action": "control",
          "nextStepID": "welcome-control-002"
        },
        {
          "type": "split",
          "label": "Group B",
          "action": "variant",
          "nextStepID": "welcome-variant-003"
        }
      ]
    },
    {
      "id": "welcome-control-002",
      "type": "message",
      "label": "Welcome Message Control",
      "content": "Standard welcome with discount",
      "messageText": "Hi {{first_name}}! Welcome to {{brand_name}}! Here's 20% off your first order: WELCOME20",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "percentage",
      "discountValue": "20",
      "discountCode": "WELCOME20",
      "discountEmail": "",
      "discountExpiry": "",
      "events": [
        {
          "type": "reply",
          "intent": "shop",
          "nextStepID": "show-products-004",
          "description": "Customer wants to shop"
        },
        {
          "type": "noreply",
          "after": {"value": 2, "unit": "hours"},
          "nextStepID": "followup-005",
          "description": "No response after 2 hours"
        }
      ]
    },
    {
      "id": "welcome-variant-003",
      "type": "message",
      "label": "Welcome Message Variant",
      "content": "Personalized welcome with discount",
      "messageText": "Hi {{first_name}}! We're excited to have you at {{brand_name}}! As a special welcome, enjoy 20% off: VIP20",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "percentage",
      "discountValue": "20",
      "discountCode": "VIP20",
      "discountEmail": "",
      "discountExpiry": "",
      "events": [
        {
          "type": "reply",
          "intent": "shop",
          "nextStepID": "show-products-004",
          "description": "Customer wants to shop"
        },
        {
          "type": "noreply",
          "after": {"value": 2, "unit": "hours"},
          "nextStepID": "followup-005",
          "description": "No response after 2 hours"
        }
      ]
    },
    {
      "id": "show-products-004",
      "type": "product_choice",
      "label": "Featured Products",
      "content": "Show popular products",
      "messageType": "standard",
      "messageText": "Check out our popular products:\n\n{{Product List}}\n\nReply with number to purchase!",
      "productSelection": "popularity",
      "products": [
        {"id": "prod-001", "label": "Bestseller Item", "showLabel": true, "uniqueId": 1},
        {"id": "prod-002", "label": "Popular Choice", "showLabel": true, "uniqueId": 2},
        {"id": "prod-003", "label": "Customer Favorite", "showLabel": true, "uniqueId": 3}
      ],
      "productImages": true,
      "discountType": "percentage",
      "discountValue": "20",
      "discountCode": "WELCOME20",
      "events": [
        {
          "type": "reply",
          "intent": "buy",
          "nextStepID": "purchase-006",
          "description": "Customer wants to buy"
        }
      ]
    },
    {
      "id": "purchase-006",
      "type": "purchase",
      "label": "Process Purchase",
      "content": "Complete customer purchase",
      "cartSource": "latest",
      "products": [],
      "discountType": "percentage",
      "discountValue": "20",
      "discountCode": "WELCOME20",
      "discountEmail": "",
      "events": [
        {
          "type": "default",
          "nextStepID": "thank-you-007"
        }
      ]
    },
    {
      "id": "thank-you-007",
      "type": "message",
      "label": "Thank You Message",
      "content": "Send purchase confirmation",
      "messageText": "Thank you {{first_name}}! Your order is confirmed. Enjoy your 20% savings!",
      "sendContactCard": true,
      "discountType": "none",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow-008"
        }
      ]
    },
    {
      "id": "followup-005",
      "type": "message",
      "label": "Follow Up Reminder",
      "content": "Send discount reminder",
      "messageText": "Hi {{first_name}}! Just a reminder about your 20% discount code. Don't miss out on this special offer!",
      "discountType": "percentage",
      "discountValue": "20",
      "discountCode": "WELCOME20",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow-008"
        }
      ]
    },
    {
      "id": "end-flow-008",
      "type": "end",
      "label": "Campaign End",
      "content": "End of discount campaign"
    }
  ]
}
```

## 🚨 Validation Rules

### Required for all nodes:
- ✅ `id`: Unique string
- ✅ `type`: Valid node type
- ✅ `label`: Display string
- ✅ `content`: Description string
- ✅ `active`: Boolean (default: true)
- ✅ `parameters`: Object (default: {})

### Required for events:
- ✅ `type`: Event type
- ✅ `nextStepID`: Target node ID
- ✅ `active`: Boolean (default: true)
- ✅ `parameters`: Object (default: {})
- ✅ `intent`: For type="reply"
- ✅ `after`: For type="noreply"
- ✅ `label` + `action`: For type="split"

### Unique ID Rules:
- ✅ Each `step.id` must be unique
- ✅ Each `event.nextStepID` must point to an existing `step.id`
- ✅ All `nextStepID` in events must be unique (no 2 events pointing to same target)

### Node-specific Requirements:
- ✅ MESSAGE: `messageText` required
- ✅ DELAY: `time` and `period` required
- ✅ SEGMENT: `conditions` array required
- ✅ PRODUCT_CHOICE: `products` array required
- ✅ PURCHASE: `cartSource` and `products` array required
- ✅ PROPERTY: `properties` array required
- ✅ QUIZ: `questions` array required

## 🎨 Best Practices

1. **Counter-based IDs**: `welcome-001`, `products-002`, `purchase-003`
2. **Descriptive Labels**: "Welcome Message" instead of "Node 1"
3. **Clear Flow Logic**: Each node should have a clear purpose
4. **Handle All Paths**: Always have paths for reply, noreply, and split options
5. **Variables Usage**: Use `{{variable}}` in messageText
6. **Discount Strategy**: Try to use appropriate discount types
7. **End Node**: Always end with END node
8. **Experiment Logic**: Use EXPERIMENT + SPLIT_GROUP nodes for A/B testing
9. **Property Updates**: Use PROPERTY nodes for customer data tracking
10. **Rate Limiting**: Use RATE_LIMIT to control message frequency

## 📄 Common Campaign Templates

### 1. Basic Welcome Campaign
Start → Message → Product Choice → Purchase → Thank You → END

### 2. VIP Campaign with A/B Testing
Start → Experiment (A/B) → Message (Control/Variant) → Segment → VIP Products → Purchase → Thank You → END

### 3. Flash Sale Campaign
Start → Announce → Product Choice → Urgency Timer → Purchase → Thank You → END

### 4. Re-engagement Campaign
Start → Segment (Inactive) → Special Offer → Product Choice → Purchase → Thank You → Property Update → END

### 5. Quiz Marketing Campaign
Start → Quiz → Property Update → Product Recommendation → Purchase → Thank You → END

### 6. Drip Campaign with Rate Limit
Start → Rate Limit → Message 1 → Delay → Message 2 → Delay → Message 3 → END

---

**This document provides EXACT JSON structure for AI based on actual EditDrawer implementations, ensuring generation of production-ready flows without requiring many modifications!**