# FlowBuilder AI JSON Generation Complete Guide

This document provides the complete JSON structure for all node types in FlowBuilder, helping AI generate accurate data for each edit drawer.

## General Structure

```javascript
{
  "initialStepID": "id-of-first-node",
  "steps": [
    // Array of nodes – DO NOT include the START node (the system creates it automatically)
  ]
}
```

---

## 1. MESSAGE Node

```javascript
{
  "id": "unique-id",
  "type": "message",

  // === Content Fields ===
  "content": "Main message text content", // REQUIRED - Primary display field
  "text": "Main message text content",    // Same as content (backward compatibility)
  "label": "Optional label for this message step",

  // === Image Settings ===
  "addImage": false,
  "imageUrl": "https://example.com/image.jpg", // Only when addImage = true

  // === Contact Card ===
  "sendContactCard": false,

  // === Discount Settings ===
  "discountType": "none", // "none" | "percentage" | "amount" | "code"
  "discountValue": "",    // Only when discountType != "none"
  "discountCode": "",     // Only when discountType = "code"
  "discountEmail": "",    // Optional email restriction
  "discountExpiry": "",   // Optional expiry date: "2024-12-31T23:59:59"

  // === Status Fields ===
  "handled": false,
  "aiGenerated": false,
  "active": true,
  "parameters": {},

  // === Events ===
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

**Variables you can use in `content`:**
- `{{brand_name}}` — Brand name  
- `{{store_url}}` — Store URL  
- `{{first_name}}` — Customer first name  
- `{{customer_timezone}}` — Customer time zone  
- `{{agent_name}}` — Agent name  
- `{{opt_in_terms}}` — Opt-in terms

---

## 2. SEGMENT Node

```javascript
{
  "id": "unique-id",
  "type": "segment",

  // === Basic Fields ===
  "label": "Optional label for this segment step",

  // === Conditions Format (New - Preferred) ===
  "conditions": [
    {
      "id": 1,
      "type": "event", // "event" | "property" | "refill"
      "operator": "has", // "has" | "has_not"

      // Event Conditions (type="event")
      "action": "placed_order", // "placed_order" | "clicked_link" | "viewed_product" | "added_product_to_cart" | "started_checkout"
      "filter": "all orders",   // "all orders" | "all clicks" | "all product views" | "all cart updates" | "all checkout updates"

      // Property Conditions (type="property")
      "propertyName": "customer_type",        // Only for type="property"
      "propertyValue": "vip",                 // Only for type="property"
      "propertyOperator": "with a value of",  // "that exists" | "does not exist" | "with a value of" | "with a value not equal to" | "with a value containing" | "with a value not containing"
      "showPropertyValueInput": false,        // Only for type="property"
      "showPropertyOperatorOptions": false,   // Only for type="property"

      // Time Settings
      "timePeriod": "within the last 30 Days",
      "timePeriodType": "relative",
      "customTimeValue": "7",   // Only when timePeriod is not the default
      "customTimeUnit": "Days", // "Minutes" | "Hours" | "Days"
      "showTimePeriodOptions": false,

      // Display Settings
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

  // === Legacy Format ===
  "segmentDefinition": {
    "operator": "OR", // "AND" | "OR"
    "segments": [
      {
        "type": "inclusion", // "inclusion" | "exclusion"
        "customerAction": {
          "type": "event", // "event" | "customer_property"
          "event": "onetext_external_order_create", // "onetext_external_order_create" | "onetext_link_click" | "onetext_external_product_view" | "onetext_external_cart_update" | "onetext_external_checkout_update"
          "propertyName": "customer_type", // Only for type="customer_property"
          "propertyValue": "vip",          // Only for type="customer_property"
          "filterOperator": "equals"       // "equals" | "not_equals" | "contains" | "not_contains" | "exists" | "not_exists"
        },
        "period": {
          "type": "within_last", // "within_last" | "all_time"
          "value": {
            "unit": "day", // "minute" | "hour" | "day"
            "value": 30
          }
        }
      }
    ]
  },

  "active": true,
  "parameters": {},

  // === Events (Usually 2 branches) ===
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

---

## 3. DELAY Node

```javascript
{
  "id": "unique-id",
  "type": "delay",

  // === Basic Fields ===
  "time": "5",        // Required - delay value as a string
  "period": "Minutes",// Required - "Seconds" | "Minutes" | "Hours" | "Days"

  // === Structured Format ===
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

---

## 4. SCHEDULE Node

```javascript
{
  "id": "unique-id",
  "type": "schedule",

  // === Basic Fields ===
  "label": "Schedule configuration label",
  "content": "Display content (usually same as label)",

  // === Configuration ===
  "schedule": {
    // Schedule configuration object (handled by the backend)
  },

  "active": true,
  "parameters": {},

  // === Events (Usually time-based branches) ===
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

---

## 5. EXPERIMENT Node

```javascript
{
  "id": "unique-id",
  "type": "experiment",

  // === Basic Fields ===
  "label": "Optional label for experiment step",
  "experimentName": "Welcome Message Test", // Required
  "version": "1",
  "content": "Display content: Welcome Message Test(v1)",

  // === Configuration ===
  "experimentConfig": {
    // Experiment configuration (handled by the backend)
  },

  "active": true,
  "parameters": {},

  // === Events (Usually 2 branches: Group A & Group B) ===
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

---

## 6. RATE_LIMIT Node

```javascript
{
  "id": "unique-id",
  "type": "rate_limit",

  // === Basic Fields ===
  "occurrences": "12", // Required - number as a string
  "timespan": "11",    // Required - timespan as a string
  "period": "Minutes", // Required - "Minutes" | "Hours" | "Days"

  // === Structured Format ===
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

---

## 7. REPLY Node

```javascript
{
  "id": "unique-id",
  "type": "reply",

  // === Basic Fields ===
  "enabled": true,
  "intent": "yes", // Required - intent name to trigger
  "description": "Optional description of the intent for better context",
  "label": "yes", // Display label (usually same as intent)

  // === Configuration ===
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

---

## 8. NO_REPLY Node

```javascript
{
  "id": "unique-id",
  "type": "no_reply",

  // === Basic Fields ===
  "enabled": true,
  "value": 6,       // Required - wait time as a number
  "unit": "hours",  // Required - "seconds" | "minutes" | "hours" | "days"
  "label": "No Reply",
  "content": "Display content: 6 hours",

  // === Structured Format ===
  "after": {
    "value": 6,
    "unit": "hours"
  },

  // === Legacy Format ===
  "seconds": 21600, // 6 hours in seconds
  "period": "Hours",

  // === Configuration ===
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

## 9. SPLIT Node

```javascript
{
  "id": "unique-id",
  "type": "split",

  // === Basic Fields ===
  "enabled": true,
  "label": "include",     // Required - split condition label
  "action": "include",    // Split action
  "description": "Optional description of split condition",
  "content": "Display content: include",

  // === Configuration ===
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

---

## 10. PROPERTY Node

```javascript
{
  "id": "unique-id",
  "type": "property",

  // === Basic Fields ===
  "label": "Customer Property Step",
  "content": "Display content: Customer Property Step",

  // === Properties Array ===
  "properties": [
    {
      "id": 1,
      "name": "customer_type", // Required property name
      "value": "vip"           // Required property value
    },
    {
      "id": 2,
      "name": "last_purchase_category",
      "value": "electronics"
    }
  ],

  // === Configuration ===
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

## 11. PRODUCT_CHOICE Node

```javascript
{
  "id": "unique-id",
  "type": "product_choice",

  // === Basic Fields ===
  "label": "Optional label for product choice step",

  // === Message Configuration ===
  "messageType": "standard", // "standard" | "personalized"
  "messageText": "Reply to buy:\n\nProduct List", // Required message text
  "text": "Reply to buy:\n\nProduct List",        // Backward compatibility
  "prompt": "Which product would you like to purchase?", // Alternative to messageText

  // === Product Selection ===
  "productSelection": "manually", // "automatically" | "popularity" | "recently_viewed" | "manually"
  "productSelectionPrompt": "Show me products you think I'll like based on my prior purchase, cart, browse behavior, profile properties, and recent messages. If you don't have enough information, show me popular products.", // Only when productSelection="automatically"

  // === Manual Products (Only when productSelection="manually") ===
  "products": [
    {
      "id": "prod-123",          // Required product ID
      "label": "Premium Headphones", // Optional product label
      "showLabel": true,         // Whether to show label
      "uniqueId": 1              // Internal tracking ID
    }
  ],

  // === Options ===
  "productImages": true,     // Send product images
  "customTotals": false,     // Add custom totals
  "customTotalsAmount": "Shipping", // Custom shipping amount
  "discountExpiry": false,   // Discount has expiry
  "discountExpiryDate": "2024-12-31T23:59:59", // Expiry date when enabled
  "discount": "None",        // Discount type: "None" | "10%" | "$5" | "SAVE20"

  // === Configuration ===
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

**Variables you can use in `messageText`:**
- `{{Product List}}` — Product list with prices  
- `{{Product List Without Prices}}` — Product list without prices  
- `{{Discount Label}}` — Discount label  
- `{{brand_name}}`, `{{first_name}}`, etc.

---

## 12. END Node

```javascript
{
  "id": "unique-id",
  "type": "end",

  // === Basic Fields ===
  "label": "End",

  "active": true,
  "parameters": {},
  "events": [] // End node has no events
}
```

---

---

## 13. PURCHASE_OFFER Node

```javascript
{
  "id": "unique-id",
  "type": "purchase_offer",

  // === Basic Fields ===
  "label": "Optional label for purchase offer step",
  "content": "Display content from label",

  // === Message Configuration ===
  "messageType": "standard",        // "standard" | "personalized"
  "messageText": "Reply 'yes' to buy:\n\nCart List", // Required message text
  "text": "Reply 'yes' to buy:\n\nCart List",        // Backward compatibility

  // === Cart Configuration ===
  "cartSource": "manual", // "manual" | "latest"

  // === Manual Products (Only when cartSource="manual") ===
  "products": [
    {
      "productVariantId": "123123", // Required product variant ID
      "quantity": "3",              // Required quantity as a string
      "uniqueId": 1                 // Internal tracking ID
    }
  ],

  // === Discount Settings ===
  "discount": false,            // Enable/disable discount
  "discountType": "percentage", // "percentage" | "amount" | "code" (only when discount = true)
  "discountPercentage": "",     // Only when discountType = "percentage"
  "discountAmount": "",         // Only when discountType = "amount"
  "discountCode": "",           // Only when discountType = "code"
  "discountAmountLabel": "",    // Optional label for discount code
  "discountEmail": "",          // Optional email restriction
  "discountExpiry": false,      // Discount has expiry
  "discountExpiryDate": "2024-12-31T23:59:59", // Expiry date when enabled

  // === Additional Options ===
  "customTotals": false,      // Add custom totals
  "shippingAmount": "",       // Custom shipping amount (only when customTotals = true)
  "includeProductImage": true,// Send product images
  "skipForRecentOrders": true,// Skip for recent orders

  // === Configuration ===
  "purchaseOfferConfig": {
    // Purchase offer configuration (handled by the backend)
  },

  "active": true,
  "parameters": {},

  // === Events ===
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

**Variables you can use in `messageText`:**
- **Brand Name** — Brand name  
- **First Name** — Customer first name  
- **Discount Label** — Discount label  
- **Cart List** — List of products in the cart  
- **Purchase Link** — Purchase link  
- **Agent Name** — Agent name

---

## 14. PURCHASE Node

```javascript
{
  "id": "unique-id",
  "type": "purchase",

  // === Cart Source Configuration ===
  "cartSource": "manual", // "manual" | "latest" - Required

  // === Manual Products (Only when cartSource="manual") ===
  "products": [
    {
      "productVariantId": "prod-123", // Required product variant ID
      "quantity": "1",                // Required quantity as a string
      "uniqueId": 1                   // Internal tracking ID
    }
  ],

  // === Options ===
  "discount": false,                 // Add discount to order
  "customTotals": false,             // Add custom totals
  "shippingAmount": "",              // Custom shipping amount (only when customTotals = true)
  "sendReminderForNonPurchasers": false, // Send reminder for non-purchasers
  "allowAutomaticPayment": false,    // Allow automatic payment completion

  // === Configuration ===
  "purchaseConfig": {
    // Purchase configuration (handled by the backend)
  },

  "active": true,
  "parameters": {},

  // === Events ===
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

## 15. LIMIT Node

```javascript
{
  "id": "unique-id",
  "type": "limit",

  // === Basic Fields ===
  "occurrences": "5", // Required - number of occurrences as a string
  "timespan": "1",    // Required - timespan as a string
  "period": "Hours",  // Required - "Minutes" | "Hours" | "Days"

  // === Structured Format ===
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

**Note**: The LIMIT node uses the same structure as RATE_LIMIT but may have different backend handling.

---

## 16. SPLIT Variants

SPLIT variants are variations of the SPLIT node with the same structure:

### SPLIT_GROUP Node (Experiment Branch)
```javascript
{
  "id": "unique-id",
  "type": "split_group",

  // === Basic Fields ===
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

### SPLIT_RANGE Node (Schedule Branch)
```javascript
{
  "id": "unique-id",
  "type": "split_range",

  // === Basic Fields ===
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

**Note**: SPLIT_GROUP and SPLIT_RANGE use the same structure as the SPLIT node but are generated automatically by the EXPERIMENT and SCHEDULE nodes.

---

## Complete Workflow Example

```javascript
{
  "initialStepID": "welcome-message",
  "steps": [
    {
      "id": "welcome-message",
      "type": "message",
      "content": "Hi {{first_name}}! Welcome to our store. Would you like to see our new products?",
      "text": "Hi {{first_name}}! Welcome to our store. Would you like to see our new products?",
      "addImage": false,
      "sendContactCard": true,
      "discountType": "percentage",
      "discountValue": "10",
      "discountExpiry": "2024-12-31T23:59:59",
      "handled": false,
      "aiGenerated": false,
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "welcome-reply",
          "type": "reply",
          "intent": "yes",
          "description": "Customer wants to see new products",
          "nextStepID": "segment-check",
          "active": true,
          "parameters": {}
        },
        {
          "id": "welcome-noreply",
          "type": "noreply",
          "after": {
            "value": 24,
            "unit": "hours"
          },
          "nextStepID": "followup-delay",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "segment-check",
      "type": "segment",
      "label": "VIP Customer Check",
      "conditions": [
        {
          "id": 1,
          "type": "event",
          "operator": "has",
          "action": "placed_order",
          "filter": "all orders",
          "timePeriod": "within the last 30 Days",
          "timePeriodType": "relative"
        }
      ],
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "vip-yes",
          "type": "split",
          "label": "include",
          "action": "include",
          "nextStepID": "vip-offer",
          "active": true,
          "parameters": {}
        },
        {
          "id": "vip-no",
          "type": "split",
          "label": "exclude",
          "action": "exclude",
          "nextStepID": "regular-products",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "vip-offer",
      "type": "purchase_offer",
      "label": "VIP Special Offer",
      "messageType": "personalized",
      "messageText": "Hi {{first_name}}! As a VIP customer, here's an exclusive offer just for you:\n\n{{Cart List}}\n\nReply YES to claim your special discount!",
      "cartSource": "manual",
      "products": [
        {
          "productVariantId": "vip-123",
          "quantity": "1",
          "uniqueId": 1
        }
      ],
      "discount": true,
      "discountType": "percentage",
      "discountPercentage": "20",
      "discountExpiry": true,
      "discountExpiryDate": "2024-12-31T23:59:59",
      "includeProductImage": true,
      "skipForRecentOrders": true,
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "vip-buy",
          "type": "reply",
          "intent": "yes",
          "nextStepID": "purchase-process",
          "active": true,
          "parameters": {}
        },
        {
          "id": "vip-noreply",
          "type": "noreply",
          "after": {
            "value": 2,
            "unit": "hours"
          },
          "nextStepID": "followup-message",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "regular-products",
      "type": "product_choice",
      "messageType": "standard",
      "messageText": "Reply to buy:\n\n{{Product List}}",
      "productSelection": "popularity",
      "productImages": true,
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "regular-buy",
          "type": "reply",
          "intent": "buy",
          "nextStepID": "purchase-process",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "purchase-process",
      "type": "purchase",
      "cartSource": "latest",
      "discount": false,
      "customTotals": false,
      "sendReminderForNonPurchasers": true,
      "allowAutomaticPayment": false,
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "purchase-complete",
          "type": "default",
          "nextStepID": "end-node",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "followup-delay",
      "type": "delay",
      "time": "5",
      "period": "Minutes",
      "delay": {
        "value": "5",
        "unit": "Minutes"
      },
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "followup-event",
          "type": "default",
          "nextStepID": "followup-message",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "followup-message",
      "type": "message",
      "content": "Just leaving this with you. You might be busy. Reach out when you're ready!",
      "text": "Just leaving this with you. You might be busy. Reach out when you're ready!",
      "handled": false,
      "aiGenerated": false,
      "active": true,
      "parameters": {},
      "events": [
        {
          "id": "followup-end",
          "type": "default",
          "nextStepID": "end-node",
          "active": true,
          "parameters": {}
        }
      ]
    },
    {
      "id": "end-node",
      "type": "end",
      "label": "End",
      "active": true,
      "parameters": {},
      "events": []
    }
  ]
}
```

## Important Rules for AI

1. **ID Generation**: Generate a unique ID for every node and event.  
2. **`initialStepID`**: Must point to the ID of the first node in the `steps` array.  
3. **`nextStepID`**: Must point to the ID of another node within the same workflow.  
4. **Required Fields**: Ensure all required fields have values.  
5. **Event Types**:  
   - `default`: Direct connection  
   - `reply`: Requires `intent` and `description`  
   - `noreply`: Requires an `after` object  
   - `split`: Requires `label` and `action`  
6. **Backward Compatibility**: Both legacy and new formats are supported.  
7. **Active Status**: Default is `true` for all nodes and events.  
8. **Parameters**: Always include an empty object if there are no custom parameters.  
9. **SPLIT Variants**: `SPLIT_GROUP` and `SPLIT_RANGE` are variants of SPLIT, generated automatically by EXPERIMENT and SCHEDULE nodes.  
10. **Purchase vs. Product Choice**: Use the **PURCHASE** node type for direct purchases; use **PRODUCT_CHOICE** for customer selection.  

With this complete structure, AI can generate accurate, fully-formed workflow JSON!
