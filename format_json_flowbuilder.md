# AI Flow JSON Structure - Simplified JSON Structure for AI Generation

Simple JSON structure focused on tree-based parent-child flow logic. No need for position, style, edges - only parent-child relationships are required.

---

## 1. Overall JSON Structure

### Basic Flow Structure
```json
{
  "name": "Campaign Name",
  "description": "Campaign description",
  "initialStepID": "welcome-message",
  "steps": [
    // Array of nodes - DOES NOT include START node
  ]
}
```

### Root Node Structure (Start)
```json
// START node is automatically created, no need to declare
{
  "id": "start",
  "type": "START"
}
```

---

## 2. Node Structure Template

### Message Node
```json
{
  "id": "unique-node-id",
  "type": "message",
  "label": "Welcome Message",
  "content": "Send welcome to new customers",
  "messageText": "Hi {{first_name}}! Welcome to {{brand_name}}!",
  "addImage": false,
  "imageUrl": "",
  "sendContactCard": true,
  "discountType": "percentage",
  "discountValue": "10",
  "discountCode": "WELCOME10",
  "events": [
    {
      "type": "reply",
      "intent": "yes",
      "nextStepID": "product-showcase",
      "description": "Customer interested"
    },
    {
      "type": "noreply",
      "after": { "value": 24, "unit": "hours" },
      "nextStepID": "followup-message",
      "description": "No response after 24h"
    }
  ]
}
```

### Segment Node
```json
{
  "id": "vip-check",
  "type": "segment",
  "label": "VIP Customer Check",
  "content": "Check if customer is VIP",
  "conditions": [
    {
      "type": "event",
      "action": "placed_order",
      "timePeriod": "within the last 30 days"
    }
  ],
  "events": [
    {
      "type": "split",
      "label": "VIP Customer",
      "action": "include",
      "nextStepID": "vip-offer"
    },
    {
      "type": "split",
      "label": "Regular Customer",
      "action": "exclude",
      "nextStepID": "regular-offer"
    }
  ]
}
```

---

## 3. Complete AI Prompt Examples

### Template for AI:
```
Create a JSON flow for SMS campaign with the objective: [CAMPAIGN OBJECTIVE]

Requirements:
- Start from welcome node
- Segment customers (VIP/Regular)
- Send appropriate offers
- Handle no-reply scenarios
- End with thank you message

Generate JSON following this structure:
{
  "name": "Campaign Name",
  "description": "Campaign description",
  "initialStepID": "first-node-id",
  "steps": [...]
}
```

---

## 4. Campaign Examples

### Example 1: Welcome Campaign for New Customers
```json
{
  "name": "New Customer Welcome Campaign",
  "description": "Welcome new customers and drive first purchase",
  "initialStepID": "welcome-message",
  "steps": [
    {
      "id": "welcome-message",
      "type": "message",
      "label": "Welcome Message",
      "content": "Send welcome with discount",
      "messageText": "Hi {{first_name}}! Welcome to {{brand_name}}! Here's 10% off your first order: {{store_url}}",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "percentage",
      "discountValue": "10",
      "discountCode": "WELCOME10",
      "events": [
        {
          "type": "reply",
          "intent": "interested",
          "nextStepID": "product-choice",
          "description": "Customer wants to see products"
        },
        {
          "type": "noreply",
          "after": { "value": 24, "unit": "hours" },
          "nextStepID": "followup-reminder",
          "description": "No response after 24h"
        }
      ]
    },
    {
      "id": "product-choice",
      "type": "product_choice",
      "label": "Product Selection",
      "content": "Show popular products",
      "messageType": "standard",
      "messageText": "Check out our popular products:\n\n{{Product List}}\n\nReply with number to buy!",
      "productSelection": "popularity",
      "products": [
        { "id": "prod-001", "label": "Premium Item", "uniqueId": 1 },
        { "id": "prod-002", "label": "Popular Item", "uniqueId": 2 }
      ],
      "productImages": true,
      "events": [
        {
          "type": "reply",
          "intent": "buy",
          "nextStepID": "purchase-process",
          "description": "Customer wants to purchase"
        }
      ]
    },
    {
      "id": "followup-reminder",
      "type": "message",
      "label": "Follow-up Reminder",
      "content": "Remind about welcome offer",
      "messageText": "Hi {{first_name}}! Just a reminder about your 10% welcome discount. It expires soon!",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": false,
      "discountType": "percentage",
      "discountValue": "10",
      "discountCode": "WELCOME10",
      "events": [
        {
          "type": "reply",
          "intent": "interested",
          "nextStepID": "product-choice",
          "description": "Customer interested after reminder"
        },
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "End flow if no response"
        }
      ]
    },
    {
      "id": "purchase-process",
      "type": "purchase",
      "label": "Complete Purchase",
      "content": "Process customer purchase",
      "cartSource": "latest",
      "events": [
        {
          "type": "default",
          "nextStepID": "thank-you-message",
          "description": "Purchase successful"
        }
      ]
    },
    {
      "id": "thank-you-message",
      "type": "message",
      "label": "Thank You",
      "content": "Send thank you message",
      "messageText": "Thank you {{first_name}}! Your order is confirmed. You'll receive tracking details soon.",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "none",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "End campaign"
        }
      ]
    },
    {
      "id": "end-flow",
      "type": "end",
      "label": "End Campaign",
      "content": "Campaign completed"
    }
  ]
}
```

### Example 2: Abandoned Cart Recovery
```json
{
  "name": "Abandoned Cart Recovery Campaign",
  "description": "Recover customers who abandoned their cart",
  "initialStepID": "cart-abandonment-check",
  "steps": [
    {
      "id": "cart-abandonment-check",
      "type": "segment",
      "label": "Cart Abandonment Check",
      "content": "Check for abandoned carts",
      "conditions": [
        {
          "type": "event",
          "action": "added_product_to_cart",
          "timePeriod": "within the last 2 hours"
        }
      ],
      "events": [
        {
          "type": "split",
          "label": "Has Cart",
          "action": "include",
          "nextStepID": "first-reminder"
        },
        {
          "type": "split",
          "label": "No Cart",
          "action": "exclude",
          "nextStepID": "end-flow"
        }
      ]
    },
    {
      "id": "first-reminder",
      "type": "message",
      "label": "First Cart Reminder",
      "content": "Remind about abandoned cart",
      "messageText": "Hi {{first_name}}! Did you forget something? Your cart is waiting: {{Cart Link}}",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": false,
      "discountType": "none",
      "events": [
        {
          "type": "reply",
          "intent": "continue",
          "nextStepID": "purchase-process",
          "description": "Customer wants to complete purchase"
        },
        {
          "type": "noreply",
          "after": { "value": 2, "unit": "hours" },
          "nextStepID": "second-reminder",
          "description": "No response after 2 hours"
        }
      ]
    },
    {
      "id": "second-reminder",
      "type": "purchase_offer",
      "label": "Cart with Discount",
      "content": "Send cart with discount offer",
      "messageType": "personalized",
      "messageText": "Hi {{first_name}}! Complete your order now with 15% off:\n\n{{Cart List}}\n\nReply YES to claim discount!",
      "cartSource": "latest",
      "discount": true,
      "discountType": "percentage",
      "discountPercentage": "15",
      "discountExpiry": true,
      "discountExpiryDate": "2024-12-31T23:59:59Z",
      "includeProductImage": true,
      "events": [
        {
          "type": "reply",
          "intent": "yes",
          "nextStepID": "purchase-process",
          "description": "Customer accepts discount offer"
        },
        {
          "type": "noreply",
          "after": { "value": 4, "unit": "hours" },
          "nextStepID": "final-reminder",
          "description": "No response after 4 hours"
        }
      ]
    },
    {
      "id": "final-reminder",
      "type": "message",
      "label": "Final Reminder",
      "content": "Last chance to complete purchase",
      "messageText": "Hi {{first_name}}! Your cart items are selling fast. Complete your order before they're gone!",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": false,
      "discountType": "none",
      "events": [
        {
          "type": "reply",
          "intent": "buy",
          "nextStepID": "purchase-process",
          "description": "Customer decides to purchase"
        },
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "End campaign - no purchase"
        }
      ]
    },
    {
      "id": "purchase-process",
      "type": "purchase",
      "label": "Complete Purchase",
      "content": "Process recovered cart purchase",
      "cartSource": "latest",
      "events": [
        {
          "type": "default",
          "nextStepID": "purchase-confirmation",
          "description": "Cart recovered successfully"
        }
      ]
    },
    {
      "id": "purchase-confirmation",
      "type": "message",
      "label": "Purchase Confirmation",
      "content": "Confirm recovered purchase",
      "messageText": "Great choice {{first_name}}! Your order has been confirmed. You saved with our recovery offer!",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "none",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "Campaign completed successfully"
        }
      ]
    },
    {
      "id": "end-flow",
      "type": "end",
      "label": "End Campaign",
      "content": "Campaign completed"
    }
  ]
}
```

### Example 3: VIP Customer Re-engagement
```json
{
  "name": "VIP Customer Re-engagement Campaign",
  "description": "Re-engage VIP customers who haven't purchased recently",
  "initialStepID": "vip-segment-check",
  "steps": [
    {
      "id": "vip-segment-check",
      "type": "segment",
      "label": "VIP Customer Check",
      "content": "Identify VIP customers inactive for 30+ days",
      "conditions": [
        {
          "type": "event",
          "action": "placed_order",
          "operator": "has_not",
          "timePeriod": "more than 30 days ago"
        },
        {
          "type": "property",
          "propertyName": "customer_type",
          "propertyValue": "vip",
          "propertyOperator": "with a value of"
        }
      ],
      "events": [
        {
          "type": "split",
          "label": "VIP Inactive",
          "action": "include",
          "nextStepID": "vip-exclusive-offer"
        },
        {
          "type": "split",
          "label": "Not VIP Inactive",
          "action": "exclude",
          "nextStepID": "end-flow"
        }
      ]
    },
    {
      "id": "vip-exclusive-offer",
      "type": "message",
      "label": "VIP Exclusive Offer",
      "content": "Send exclusive VIP offer",
      "messageText": "Hi {{first_name}}! As our valued VIP customer, we miss you! Here's an exclusive 25% discount just for you:\n\n{{Personalized Products}}",
      "addImage": true,
      "imageUrl": "https://example.com/vip-offer.jpg",
      "sendContactCard": true,
      "discountType": "percentage",
      "discountValue": "25",
      "discountCode": "VIPBACK25",
      "discountExpiry": "2024-12-31T23:59:59Z",
      "events": [
        {
          "type": "reply",
          "intent": "interested",
          "nextStepID": "vip-product-choice",
          "description": "VIP interested in offer"
        },
        {
          "type": "noreply",
          "after": { "value": 6, "unit": "hours" },
          "nextStepID": "vip-personal-followup",
          "description": "No response after 6 hours"
        }
      ]
    },
    {
      "id": "vip-product-choice",
      "type": "product_choice",
      "label": "VIP Product Selection",
      "content": "Show curated VIP products",
      "messageType": "personalized",
      "messageText": "Based on your previous purchases, we think you'll love:\n\n{{VIP Product List}}\n\nReply to buy with VIP priority shipping!",
      "productSelection": "manually",
      "productSelectionPrompt": "Show products based on customer's purchase history and preferences",
      "products": [
        { "id": "vip-prod-001", "label": "Premium Collection Item", "uniqueId": 1 },
        { "id": "vip-prod-002", "label": "Exclusive VIP Product", "uniqueId": 2 }
      ],
      "productImages": true,
      "discount": "25%",
      "events": [
        {
          "type": "reply",
          "intent": "buy",
          "nextStepID": "vip-purchase",
          "description": "VIP wants to purchase"
        }
      ]
    },
    {
      "id": "vip-personal-followup",
      "type": "message",
      "label": "VIP Personal Follow-up",
      "content": "Personal follow-up from VIP manager",
      "messageText": "Hi {{first_name}}, this is {{agent_name}} from {{brand_name}} VIP team. I noticed you haven't had a chance to check our exclusive offer. Is there anything I can help you with?",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "code",
      "discountCode": "VIPEXTRA30",
      "events": [
        {
          "type": "reply",
          "intent": "yes",
          "nextStepID": "vip-product-choice",
          "description": "VIP responds to personal follow-up"
        },
        {
          "type": "noreply",
          "after": { "value": 24, "unit": "hours" },
          "nextStepID": "vip-final-offer",
          "description": "No response after 24 hours"
        }
      ]
    },
    {
      "id": "vip-final-offer",
      "type": "purchase_offer",
      "label": "VIP Final Offer",
      "content": "Final VIP offer with extra bonus",
      "messageType": "personalized",
      "messageText": "{{first_name}}, this is our final VIP offer just for you:\n\n{{Cart List}}\n\nAdditional 10% off + Free VIP shipping!\n\nReply YES to claim this exclusive offer.",
      "cartSource": "manual",
      "products": [
        { "productVariantId": "vip-final-001", "quantity": "1", "uniqueId": 1 }
      ],
      "discount": true,
      "discountType": "percentage",
      "discountPercentage": "35",
      "discountExpiry": true,
      "discountExpiryDate": "2024-12-25T23:59:59Z",
      "includeProductImage": true,
      "skipForRecentOrders": false,
      "events": [
        {
          "type": "reply",
          "intent": "yes",
          "nextStepID": "vip-purchase",
          "description": "VIP accepts final offer"
        },
        {
          "type": "default",
          "nextStepID": "vip-goodbye",
          "description": "VIP doesn't respond - end campaign"
        }
      ]
    },
    {
      "id": "vip-purchase",
      "type": "purchase",
      "label": "VIP Purchase Process",
      "content": "Process VIP purchase with priority",
      "cartSource": "latest",
      "customTotals": true,
      "shippingAmount": "0",
      "sendReminderForNonPurchasers": true,
      "events": [
        {
          "type": "default",
          "nextStepID": "vip-thank-you",
          "description": "VIP purchase completed"
        }
      ]
    },
    {
      "id": "vip-thank-you",
      "type": "message",
      "label": "VIP Thank You",
      "content": "Special VIP thank you message",
      "messageText": "Thank you {{first_name}}! Your VIP order has been prioritized and will ship within 24 hours. We've added bonus VIP points to your account!",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": true,
      "discountType": "none",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "VIP campaign completed successfully"
        }
      ]
    },
    {
      "id": "vip-goodbye",
      "type": "message",
      "label": "VIP Goodbye",
      "content": "Polite goodbye to non-responsive VIP",
      "messageText": "Hi {{first_name}}, we'll keep your VIP status active and hope to see you again soon. Best regards from the {{brand_name}} team!",
      "addImage": false,
      "imageUrl": "",
      "sendContactCard": false,
      "discountType": "none",
      "events": [
        {
          "type": "default",
          "nextStepID": "end-flow",
          "description": "End VIP campaign"
        }
      ]
    },
    {
      "id": "end-flow",
      "type": "end",
      "label": "End VIP Campaign",
      "content": "VIP campaign completed"
    }
  ]
}
```

---

## 5. AI Prompt Guidelines

### Template for AI Generation:
```
You are a marketing automation expert. Create a JSON flow for an SMS campaign with the following requirements:

**Campaign Objective**: [Describe campaign goal]
**Target Audience**: [Target audience]
**Channel**: SMS Marketing
**Duration**: [Campaign duration]

**Flow Logic Requirements**:
1. [Step 1 requirement]
2. [Step 2 requirement]
3. [Step 3 requirement]
4. [Step 4 requirement]

**Required JSON Structure**:
{
  "name": "Campaign Name",
  "description": "Brief campaign description",
  "initialStepID": "first-node-id",
  "steps": [
    // Array of nodes, DOES NOT include START node
    // Each node has: id, type, label, content, and events array
    // Events connect nodes with nextStepID
  ]
}

**Available Node Types**:
- "message": Send SMS message
- "segment": Customer segmentation
- "delay": Create delay
- "product_choice": Product selection
- "purchase_offer": Send purchase offer
- "purchase": Process order
- "end": End flow

**Available Event Types**:
- "reply": Wait for reply with intent
- "noreply": Handle no reply with after
- "split": Branch with label/action
- "default": Direct connection

Create a complete JSON that can be rendered immediately.
```

### Example AI Request:
```
Create a JSON flow for "24h Flash Sale" campaign with objectives:
- Announce upcoming flash sale
- Send flash sale product list
- Create urgency with countdown
- Handle no-reply scenarios
- Confirm successful orders

Target: Customers who purchased in last 90 days
Duration: 24 hours
Products: Electronics items with 20-50% discount
```

### Expected AI Response:
AI will generate a complete JSON structure that can be rendered directly into the flow builder without modifications.

With this structure, AI can easily generate complete JSON flows by focusing on business logic, without worrying about UI positioning, styling, or complex edge configurations.

---

## 7. AI Node Field Reference - For AI Generation

Based on documentation at `/Users/tranviet/Desktop/New-sms/sms-app/frontend/components/flow-builder/docs/NODE_FIELDS_DOCUMENTATION.md`

### 7.1 MESSAGE Node - Send SMS Message
```json
{
  "id": "unique-node-id",
  "type": "message",
  "label": "Display Label",
  "content": "Node description",
  "messageText": "Main SMS content (required)",
  "text": "Backward compatibility - same as messageText",
  "addImage": false, // Attach image
  "imageUrl": "", // Image URL when addImage = true
  "sendContactCard": false, // Send contact card
  "discountType": "none", // "none" | "percentage" | "amount" | "code"
  "discountValue": "", // Discount value when type != "none"
  "discountCode": "", // Discount code when type = "code"
  "discountEmail": "", // Email restriction (optional)
  "discountExpiry": "", // Expiry date (optional)
  "events": [] // Event connections
}
```

### 7.2 DELAY Node - Create Delay
```json
{
  "id": "unique-node-id",
  "type": "delay",
  "label": "Display Label",
  "content": "Node description",
  "time": "5", // Time value (required)
  "period": "Minutes", // "Seconds" | "Minutes" | "Hours" | "Days" (required)
  "events": [] // Event connections
}
```

### 7.3 SEGMENT Node - Customer Segmentation
```json
{
  "id": "unique-node-id",
  "type": "segment",
  "label": "Display Label",
  "content": "Node description",
  "conditions": [
    {
      "id": 1,
      "type": "event", // "event" | "property"
      "operator": "has", // "has" | "has_not"
      "action": "placed_order", // "placed_order" | "clicked_link" | "viewed_product" | "added_product_to_cart" | "started_checkout"
      "filter": "all orders", // "all orders" | "all clicks" | "all product views" | "all cart updates" | "all checkout updates"
      "timePeriod": "within the last 30 Days",
      "propertyName": "customer_type", // Only when type = "property"
      "propertyValue": "vip", // Only when type = "property"
      "propertyOperator": "with a value of" // Only when type = "property"
    }
  ],
  "events": [] // Event connections (usually 2 split branches)
}
```

### 7.4 EXPERIMENT Node - A/B Testing
```json
{
  "id": "unique-node-id",
  "type": "experiment",
  "label": "Display Label",
  "content": "Node description",
  "experimentName": "Test Name", // Experiment name
  "version": "1", // Version
  "events": [] // Event connections (usually 2 branches: Group A & B)
}
```

### 7.5 SCHEDULE Node - Scheduling
```json
{
  "id": "unique-node-id",
  "type": "schedule",
  "label": "Display Label",
  "content": "Node description",
  "events": [] // Event connections (usually 2 branches: scheduled vs all other time)
}
```

### 7.6 PROPERTY Node - Update Properties
```json
{
  "id": "unique-node-id",
  "type": "property",
  "label": "Display Label",
  "content": "Node description",
  "properties": [
    {
      "id": 1,
      "name": "property_name", // Required property name
      "value": "property_value" // Required property value
    }
  ],
  "events": [] // Event connections
}
```

### 7.7 RATE_LIMIT Node - Rate Limiting
```json
{
  "id": "unique-node-id",
  "type": "rate_limit",
  "label": "Display Label",
  "content": "Node description",
  "occurrences": "12", // Number of sends (required)
  "timespan": "11", // Time period (required)
  "period": "Minutes", // "Minutes" | "Hours" | "Days" (required)
  "events": [] // Event connections
}
```

### 7.8 LIMIT Node - Limitations
```json
{
  "id": "unique-node-id",
  "type": "limit",
  "label": "Display Label",
  "content": "Node description",
  "occurrences": "5", // Number of occurrences allowed (required)
  "timespan": "1", // Time period (required)
  "period": "Hours", // "Minutes" | "Hours" | "Days" (required)
  "events": [] // Event connections
}
```

### 7.9 SPLIT Node - Branching
```json
{
  "id": "unique-node-id",
  "type": "split",
  "label": "Display Label", // Required - split condition label
  "content": "Node description",
  "enabled": true, // Enable/disable split
  "action": "include", // Split action
  "description": "Optional description of split condition",
  "events": [] // Event connections
}
```

### 7.10 REPLY Node - Wait for Reply
```json
{
  "id": "unique-node-id",
  "type": "reply",
  "label": "Display Label",
  "content": "Node description",
  "enabled": true, // Enable/disable reply
  "intent": "yes", // Required - intent name to trigger
  "description": "Optional description of the intent for better context",
  "events": [] // Event connections
}
```

### 7.11 NO_REPLY Node - Handle No Reply
```json
{
  "id": "unique-node-id",
  "type": "no_reply",
  "label": "Display Label",
  "content": "Node description",
  "enabled": true, // Enable/disable
  "value": 6, // Required - wait time as number
  "unit": "hours", // Required - "seconds" | "minutes" | "hours" | "days"
  "events": [] // Event connections
}
```

### 7.12 PURCHASE Node - Process Order
```json
{
  "id": "unique-node-id",
  "type": "purchase",
  "label": "Display Label",
  "content": "Node description",
  "cartSource": "manual", // "manual" | "latest" (required)
  "products": [ // Product list when cartSource = "manual"
    {
      "productVariantId": "variant_id", // Required
      "quantity": "1", // Required as string
      "uniqueId": 1 // Internal tracking ID
    }
  ],
  "discount": false, // Add discount to order
  "customTotals": false, // Add custom totals
  "shippingAmount": "", // Custom shipping amount when customTotals = true
  "sendReminderForNonPurchasers": false, // Send reminder
  "allowAutomaticPayment": false, // Auto payment
  "events": [] // Event connections
}
```

### 7.13 PRODUCT_CHOICE Node - Product Selection
```json
{
  "id": "unique-node-id",
  "type": "product_choice",
  "label": "Display Label",
  "content": "Node description",
  "messageType": "standard", // "standard" | "personalized" (required)
  "messageText": "Reply to buy:\n\nProduct List", // Required message text
  "text": "Backward compatibility",
  "prompt": "Alternative to messageText",
  "productSelection": "manually", // "manually" | "automatically" | "popularity" | "recently_viewed" (required)
  "productSelectionPrompt": "Show me products you think I'll like...", // When productSelection = "automatically"
  "products": [ // When productSelection = "manually"
    {
      "id": "product_id", // Required product ID
      "label": "Product Name", // Optional product label
      "showLabel": true, // Whether to show label
      "uniqueId": 1 // Internal tracking ID
    }
  ],
  "productImages": true, // Send product images
  "customTotals": false, // Add custom totals
  "customTotalsAmount": "Shipping", // Custom shipping amount
  "discountExpiry": false, // Discount has expiry
  "discountExpiryDate": "", // Expiry date when enabled
  "discount": "None", // "None" | "10%" | "$5" | "SAVE20"
  "events": [] // Event connections
}
```

### 7.14 PURCHASE_OFFER Node - Purchase Offer
```json
{
  "id": "unique-node-id",
  "type": "purchase_offer",
  "label": "Display Label",
  "content": "Node description",
  "messageType": "standard", // "standard" | "personalized" (required)
  "messageText": "Reply 'yes' to buy:\n\nCart List", // Required message text
  "text": "Backward compatibility",
  "cartSource": "manual", // "manual" | "latest" (required)
  "products": [ // When cartSource = "manual"
    {
      "productVariantId": "123123", // Required product variant ID
      "quantity": "3", // Required quantity as string
      "uniqueId": 1 // Internal tracking ID
    }
  ],
  "discount": false, // Enable/disable discount
  "discountType": "percentage", // "percentage" | "amount" | "code" (when discount = true)
  "discountPercentage": "", // When discountType = "percentage"
  "discountAmount": "", // When discountType = "amount"
  "discountCode": "", // When discountType = "code"
  "discountAmountLabel": "", // Optional label for code discount
  "discountEmail": "", // Optional email restriction
  "discountExpiry": false, // Discount has expiry
  "discountExpiryDate": "", // Expiry date when enabled
  "customTotals": false, // Add custom totals
  "shippingAmount": "", // Custom shipping amount when customTotals = true
  "includeProductImage": true, // Send product images
  "skipForRecentOrders": true, // Skip for recent orders
  "events": [] // Event connections
}
```

### 7.15 END Node - End Flow
```json
{
  "id": "unique-node-id",
  "type": "end",
  "label": "Display Label",
  "content": "Node description"
  // No events - end node terminates flow
}
```

---

## 8. Event Structure for AI

### 8.1 Event Types and Fields
```json
// Reply Event - Wait for reply with specific intent
{
  "type": "reply",
  "intent": "yes", // Required - intent name
  "nextStepID": "next-node-id", // Required
  "description": "Optional description for better intent matching"
}

// No Reply Event - Handle when no reply after time
{
  "type": "noreply",
  "after": { // Required
    "value": 2, // Wait time
    "unit": "hours" // "seconds" | "minutes" | "hours" | "days"
  },
  "nextStepID": "next-node-id" // Required
}

// Split Event - Conditional branching
{
  "type": "split",
  "label": "include", // Required - display label
  "action": "include", // Required - split action
  "nextStepID": "next-node-id", // Required
  "description": "Optional description of split condition"
}

// Default Event - Direct connection
{
  "type": "default",
  "nextStepID": "next-node-id" // Required
}
```

---

## 9. AI Guidelines for Field Values

### 9.1 Variables Available in messageText
- `{{brand_name}}` - Brand name
- `{{store_url}}` - Store URL
- `{{first_name}}` - Customer first name
- `{{customer_timezone}}` - Customer timezone
- `{{agent_name}}` - Agent name
- `{{opt_in_terms}}` - Opt-in terms
- `{{Product List}}` - Product list with prices (product_choice)
- `{{Product List Without Prices}}` - Product list without prices (product_choice)
- `{{Discount Label}}` - Discount label (product_choice)
- `{{Cart List}}` - Cart products list (purchase_offer)
- `{{Purchase Link}}` - Purchase link (purchase_offer)
- `{{Personalized Products}}` - Personalized products (product_choice automatic)
- `{{VIP Product List}}` - VIP product list

### 9.2 Time Period Values
- `"within the last 30 Days"`
- `"within the last 7 Days"`
- `"within the last 24 Hours"`
- `"more than 30 days ago"`
- `"more than 7 days ago"`
- `"all time"`

### 9.3 Common Intent Values
- `"yes"` | `"no"` | `"interested"` | `"not_interested"`
- `"buy"` | `"purchase"` | `"order"`
- `"continue"` | `"stop"` | `"unsubscribe"`
- `"help"` | `"info"` | `"details"`

### 9.4 Common Label/Action Values
- Split labels: `"include"` | `"exclude"` | `"yes"` | `"no"`
- Split actions: `"include"` | `"exclude"`
- Message labels: descriptive names like `"Welcome Message"`, `"VIP Offer"`, `"Cart Reminder"`

---

## 10. AI Best Practices

### 10.1 Required Fields Checklist
- ✅ Every node needs: `id`, `type`, `label`, `content`
- ✅ Message node needs: `messageText`
- ✅ Delay node needs: `time`, `period`
- ✅ Segment node needs: `conditions` array
- ✅ Product node needs: `messageType`, `messageText`, `productSelection`
- ✅ Purchase node needs: `cartSource`
- ✅ Every event needs: `type`, `nextStepID`
- ✅ Reply event needs: `intent`
- ✅ Noreply event needs: `after`
- ✅ Split event needs: `label`, `action`

### 10.2 Flow Logic Rules
1. **Start from initialStepID** - Always have first node
2. **End with END node** - Always terminate with end node
3. **No circular references** - Don't create loops
4. **Handle all paths** - Every branch must lead to end node
5. **Time-based escalation** - Use noreply events for follow-up
6. **Conditional branching** - Use segment/split for decision logic

### 10.3 Common Flow Patterns
1. **Welcome Pattern**: Message → Product Choice → Purchase → Thank You
2. **Recovery Pattern**: Segment Check → Reminder → Discount → Final Offer
3. **VIP Pattern**: VIP Check → Exclusive Offer → Personal Follow-up
4. **Nurture Pattern**: Message → Delay → Message → Delay → Message

### 10.4 AI Quality Checklist
- [ ] Every node has unique ID
- [ ] Every nextStepID exists in steps array
- [ ] initialStepID points to valid node
- [ ] No orphan nodes (unconnected nodes)
- [ ] Flow logic is meaningful and practical
- [ ] Message content has appropriate variables
- [ ] Time values are reasonable (not too short/long)
- [ ] Discount values are realistic (10-50% typical)
- [ ] Event intents match message content