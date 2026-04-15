/**
 * Campaign Database MCP Server - Phase 4 (Migrated to SMS App API)
 *
 * Manages campaign lifecycle by interfacing with the SMS App API:
 * - Campaign creation (POST /save-campaign)
 * - Retrieval (GET /get-campaign-by-id)
 * - Status updates
 * - Performance tracking (GET /get-campaign-roi, etc)
 *
 * Authentication:
 * - Magic Link flow: generates JWT token, exchanges for session cookie
 * - Cookie: shopify_session (cached per shop, refreshed on expiry)
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js"
import "../shared/env.js"
import Redis from "ioredis"
import {
  createPlan,
  updatePlanCampaign,
  getPlan,
  listPlans,
  type CreatePlanInput,
  type PlanPeriod,
  type CampaignSlotStatus,
} from "./plan-store.js"

// Configuration
const API_BASE_URL = process.env.SMS_APP_API_URL || "http://localhost:39000"
const REDIS_URL = process.env.REDIS_URL || "redis://localhost:6379"
const COOKIE_TTL_SECONDS = 6 * 24 * 60 * 60 // 6 days in seconds (magic link token expires in 7d)
const REDIS_KEY_PREFIX = "mcp:session:"

// Redis client (lazy init)
let redis: Redis | null = null

function getRedis(): Redis {
  if (!redis) {
    redis = new Redis(REDIS_URL, {
      maxRetriesPerRequest: 3,
      lazyConnect: true,
      retryStrategy: (times: number) => Math.min(times * 100, 3000),
    })
    redis.on("error", (err) => console.error("[Redis] Error:", err.message))
    redis.on("connect", () => console.error("[Redis] Connected"))
  }
  return redis
}

/**
 * Get cached session cookie from Redis
 */
async function getCachedCookie(shop: string): Promise<string | null> {
  try {
    const value = await getRedis().get(`${REDIS_KEY_PREFIX}${shop}`)
    return value
  } catch (err: any) {
    console.error(`[Redis] Get error for ${shop}: ${err.message}`)
    return null
  }
}

/**
 * Store session cookie in Redis with TTL
 */
async function setCachedCookie(shop: string, cookie: string): Promise<void> {
  try {
    await getRedis().setex(`${REDIS_KEY_PREFIX}${shop}`, COOKIE_TTL_SECONDS, cookie)
  } catch (err: any) {
    console.error(`[Redis] Set error for ${shop}: ${err.message}`)
  }
}

/**
 * Delete cached session cookie from Redis
 */
async function deleteCachedCookie(shop: string): Promise<void> {
  try {
    await getRedis().del(`${REDIS_KEY_PREFIX}${shop}`)
  } catch (err: any) {
    console.error(`[Redis] Del error for ${shop}: ${err.message}`)
  }
}

/**
 * Obtain a session cookie for a shop via Magic Link flow:
 * 1. Check Redis cache
 * 2. POST /magic-link/generate to get a JWT token
 * 3. GET /magic-link/login?shop=...&token=... to exchange for session cookie
 * 4. Cache the cookie in Redis for subsequent API calls
 */
async function getSessionCookie(shop: string): Promise<string> {
  // Check Redis cache first
  const cached = await getCachedCookie(shop)
  if (cached) {
    return cached
  }

  // Step 1: Generate magic link token
  const generateRes = await fetch(`${API_BASE_URL}/magic-link/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ shop, expiresIn: "7d" }),
  })

  if (!generateRes.ok) {
    const errorText = await generateRes.text()
    throw new Error(`Magic link generate failed (${generateRes.status}): ${errorText}`)
  }

  const data = await generateRes.json() as { magicLink: string }
  const magicLinkUrl = new URL(data.magicLink)
  const token = magicLinkUrl.searchParams.get("token")

  if (!token) {
    throw new Error("No token found in magic link URL")
  }

  // Step 2: Call magic link URL (don't follow redirect, capture Set-Cookie)
  // Use the exact path from the generated magic link (e.g. /magic-link?shop=...&token=...)
  const loginUrl = `${API_BASE_URL}${magicLinkUrl.pathname}${magicLinkUrl.search}`
  const loginRes = await fetch(loginUrl, { redirect: "manual" })

  // Step 3: Parse Set-Cookie headers
  const rawHeaders = loginRes.headers as any
  const setCookies: string[] = rawHeaders.raw?.()?.["set-cookie"]
    || rawHeaders.getSetCookie?.()
    || [loginRes.headers.get("set-cookie")].filter(Boolean)

  const cookieParts = setCookies
    .map((c: string) => c.split(";")[0])
    .join("; ")

  if (!cookieParts) {
    throw new Error("No session cookie returned from magic link login")
  }

  // Cache in Redis
  await setCachedCookie(shop, cookieParts)

  console.error(`[Auth] Session cookie obtained for shop: ${shop}`)
  return cookieParts
}

// Helper to make API calls with Magic Link session cookie auth
async function makeApiCall(
  endpoint: string,
  method: string = "GET",
  body?: any,
  shop?: string
): Promise<any> {
  if (!shop) {
    throw new Error("Missing required 'shop' parameter.")
  }

  // Get session cookie via Magic Link
  const sessionCookie = await getSessionCookie(shop)

  const url = new URL(`${API_BASE_URL}${endpoint}`)

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Cookie": sessionCookie,
  }

  // Append shop to query params for GET requests
  if (method === "GET") {
    url.searchParams.append("shop", shop)
  }

  const options: RequestInit = { method, headers }

  if (body) {
    options.body = JSON.stringify({ ...body, shop })
  } else if (method !== "GET") {
    options.body = JSON.stringify({ shop })
  }

  const response = await fetch(url.toString(), options)
  const responseText = await response.text()

  // Handle auth failure - clear cache and retry once
  if (response.status === 401 || response.status === 302) {
    console.error(`[Auth] Cookie expired/invalid for ${shop}, refreshing...`)
    await deleteCachedCookie(shop)

    const newCookie = await getSessionCookie(shop)
    headers["Cookie"] = newCookie
    const retryRes = await fetch(url.toString(), { ...options, headers })
    const retryText = await retryRes.text()

    try {
      const data = JSON.parse(retryText)
      if (!retryRes.ok) throw new Error(`API Error ${retryRes.status}: ${data.error || retryText}`)
      return data
    } catch {
      if (!retryRes.ok) throw new Error(`API Error ${retryRes.status}: ${retryText}`)
      return retryText
    }
  }

  // Parse response
  try {
    const data = JSON.parse(responseText)
    if (!response.ok) throw new Error(`API Error ${response.status}: ${data.error || responseText}`)
    return data
  } catch (e) {
    if (!response.ok) throw new Error(`API Error ${response.status}: ${responseText}`)
    return responseText
  }
}

// Create the MCP server
const server = new Server(
  {
    name: "campaign-db",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
)

// Handle tool listing
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "create_campaign",
        description:
          "Create a new campaign using the SMS App API. Returns the campaign ID.",
        inputSchema: {
          type: "object" as const,
          properties: {
            name: {
              type: "string",
              description: "Internal campaign name/title"
            },
            message: {
              type: "string",
              description: "Primary message text",
            },
            segment_id: {
              type: "string",
              description: "Target segment ID (required by SMS App)"
            },
            scheduled_time: {
              type: "string",
              description: "Scheduled send time in ISO8601 format (optional)",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["name", "message", "segment_id", "shop"],
        },
      },
      {
        name: "get_campaign",
        description: "Retrieve a campaign by ID from SMS App.",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID (_id from SMS App)",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "shop"],
        },
      },
      {
        name: "update_campaign_status",
        description: "Update the status of a campaign (e.g. to draft or scheduled).",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID",
            },
            status: {
              type: "string",
              description: "New status (Draft, Scheduled, etc.)",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "status", "shop"],
        },
      },
      {
        name: "schedule_campaign",
        description: "Schedule a campaign for deployment via SMS App.",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID",
            },
            scheduled_time: {
              type: "string",
              description: "Send time in ISO8601 format",
            },
            budget_cost: {
              type: "number",
              description: "Estimated cost (required for send-campaign endpoint check)"
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "scheduled_time", "shop"],
        },
      },
      {
        name: "get_campaign_performance",
        description: "Get campaign performance metrics (ROI, CTR, Conversions) from SMS App.",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "shop"],
        },
      },
      {
        name: "list_campaigns",
        description: "List campaigns from SMS App.",
        inputSchema: {
          type: "object" as const,
          properties: {
            status: {
              type: "string",
              description: "Filter by status (Sent, Draft, Scheduled, etc.)",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 10)",
            },
            page: {
              type: "number",
              description: "Page number (default: 0)"
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["shop"],
        },
      },
      {
        name: "cancel_campaign",
        description: "Cancel a scheduled campaign.",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "shop"],
        },
      },
      {
        name: "delete_campaign",
        description: "Delete a campaign permanently.",
        inputSchema: {
          type: "object" as const,
          properties: {
            campaign_id: {
              type: "string",
              description: "Campaign ID",
            },
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["campaign_id", "shop"],
        },
      },
      {
        name: "list_segments",
        description: "List available customer segments from SMS App to retrieve segment_id.",
        inputSchema: {
          type: "object" as const,
          properties: {
            shop: {
              type: "string",
              description: "Shopify domain (required)"
            }
          },
          required: ["shop"],
        },
      },

      // ──── Campaign Plan Tools ────────────────────────────────────────────
      {
        name: "create_plan",
        description: "Create and persist a campaign plan (calendar) in MongoDB. Returns plan_id. Use this after the user approves the calendar from plan-builder.",
        inputSchema: {
          type: "object" as const,
          properties: {
            shop: { type: "string", description: "Shopify domain (required)" },
            name: { type: "string", description: "Human-readable plan name, e.g. 'May Plan - Fashion'" },
            period: { type: "string", description: "Planning period: week | month | quarter | year" },
            period_start: { type: "string", description: "Period start date in ISO8601 format" },
            period_end: { type: "string", description: "Period end date in ISO8601 format" },
            industry: { type: "string", description: "Industry of the shop (fashion, beauty, etc.)" },
            goals: { type: "string", description: "Optional: merchant goals for the period" },
            campaigns: {
              type: "array",
              description: "Array of campaign slots from plan-builder output",
              items: {
                type: "object",
                properties: {
                  index: { type: "number" },
                  campaign_type: { type: "string" },
                  offer_theme: { type: "string" },
                  segment_name: { type: "string" },
                  segment_id: { type: "string" },
                  suggested_send_date: { type: "string" },
                  priority: { type: "string" },
                  rationale: { type: "string" },
                },
                required: ["index", "campaign_type", "offer_theme", "segment_name", "segment_id", "suggested_send_date", "priority"],
              },
            },
          },
          required: ["shop", "name", "period", "period_start", "period_end", "industry", "campaigns"],
        },
      },
      {
        name: "update_plan_campaign",
        description: "Update a single campaign slot in a plan after generation (set campaign_id and status). Call after each campaign is created.",
        inputSchema: {
          type: "object" as const,
          properties: {
            plan_id: { type: "string", description: "Plan ID returned by create_plan" },
            shop: { type: "string", description: "Shopify domain (required)" },
            campaign_index: { type: "number", description: "Zero-based index of the campaign slot" },
            campaign_id: { type: "string", description: "Campaign ID from create_campaign (null if failed)" },
            status: { type: "string", description: "New status: creating | created | failed" },
            error: { type: "string", description: "Error message if status is failed" },
          },
          required: ["plan_id", "shop", "campaign_index", "status"],
        },
      },
      {
        name: "get_plan",
        description: "Retrieve a campaign plan by plan_id to check status and progress.",
        inputSchema: {
          type: "object" as const,
          properties: {
            plan_id: { type: "string", description: "Plan ID" },
            shop: { type: "string", description: "Shopify domain (required)" },
          },
          required: ["plan_id", "shop"],
        },
      },
      {
        name: "list_plans",
        description: "List all campaign plans for a shop.",
        inputSchema: {
          type: "object" as const,
          properties: {
            shop: { type: "string", description: "Shopify domain (required)" },
            status: { type: "string", description: "Filter by status: active | completed | cancelled (optional)" },
          },
          required: ["shop"],
        },
      },

      // ──── Shopify Store Info Tools ─────────────────────────────────────────
      {
        name: "get_shop_info",
        description: "Get shop metadata from Shopify including timezone (for TCPA compliance) and shop details.",
        inputSchema: {
          type: "object" as const,
          properties: {
            shop: { type: "string", description: "Shopify domain (required)" },
          },
          required: ["shop"],
        },
      },
      {
        name: "get_products",
        description: "Get products from Shopify for product-specific campaigns (flash_sale, new_arrival, back_in_stock). Returns product details including prices and inventory.",
        inputSchema: {
          type: "object" as const,
          properties: {
            shop: { type: "string", description: "Shopify domain (required)" },
            filter: {
              type: "string",
              description: "Filter products: on_sale | new_arrival | back_in_stock | all (default: all)"
            },
            limit: {
              type: "number",
              description: "Max products to return (default: 50, max: 100)"
            },
          },
          required: ["shop"],
        },
      },
    ],
  }
})

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params

  if (name === "create_campaign") {
    const {
      name: title,
      message,
      segment_id,
      scheduled_time,
      shop,
    } = args as any

    // Map to POST /save-campaign
    const payload: any = {
      title,
      message,
      segment: segment_id,
      status: "Draft", // Default to Draft
      smartSend: true,
      shopNamePlacement: "suffix",
    }

    if (scheduled_time) {
      payload.schedule = "Later"
      payload.scheduledFor = scheduled_time
    }

    try {
      const result = await makeApiCall("/save-campaign", "POST", payload, shop)
      // Result: { campaign: { _id, ... } }
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: true,
            campaign_id: result.campaign?._id || result._id || "unknown",
            status: result.campaign?.status || "Draft",
            message: "Campaign created in SMS App"
          }, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error creating campaign: ${error.message}` }] }
    }
  }

  if (name === "get_campaign") {
    const { campaign_id, shop } = args as any
    try {
      const result = await makeApiCall(`/get-campaign-by-id/${campaign_id}`, "GET", undefined, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error getting campaign: ${error.message}` }] }
    }
  }

  if (name === "list_campaigns") {
    const { status, limit = 10, page = 0, shop } = args as any
    const queryParams = new URLSearchParams({
      limit: limit.toString(),
      page: page.toString()
    })

    if (status) queryParams.append("status", status)

    try {
      // Pass shop separately to handle it in makeApiCall properly
      const result = await makeApiCall(`/get-campaigns?${queryParams.toString()}`, "GET", undefined, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error listing campaigns: ${error.message}` }] }
    }
  }

  if (name === "update_campaign_status") {
    const { campaign_id, status, shop } = args as any
    try {
      // Fetch current first to get full object for update
      const currentRes = await makeApiCall(`/get-campaign-by-id/${campaign_id}`, "GET", undefined, shop)
      const current = currentRes.campaign

      if (!current) throw new Error("Campaign not found")

      const payload = {
        ...current,
        campaignId: campaign_id,
        status: status
      }

      // Note: makeApiCall will inject 'shop' automatically into POST body
      const result = await makeApiCall("/save-campaign", "POST", payload, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: true,
            campaign_id,
            new_status: result.campaign.status
          }, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error updating status: ${error.message}` }] }
    }
  }

  if (name === "schedule_campaign") {
    const { campaign_id, scheduled_time, budget_cost, shop } = args as any
    try {
      const currentRes = await makeApiCall(`/get-campaign-by-id/${campaign_id}`, "GET", undefined, shop)
      const current = currentRes.campaign

      if (!current) throw new Error("Campaign not found")

      const payload = {
        ...current,
        campaignId: campaign_id,
        schedule: "Later",
        scheduledFor: scheduled_time,
        status: "Scheduled"
      }

      await makeApiCall("/save-campaign", "POST", payload, shop)

      if (budget_cost) {
        const sendPayload = {
          campaignId: campaign_id,
          costOfCampaign: budget_cost
        }
        const sendResult = await makeApiCall("/send-campaign", "POST", sendPayload, shop)
        return {
          content: [{
            type: "text",
            text: JSON.stringify(sendResult, null, 2)
          }]
        }
      }

      return {
        content: [{
          type: "text",
          text: JSON.stringify({ success: true, message: "Campaign scheduled (soft)", scheduledFor: scheduled_time }, null, 2)
        }]
      }

    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error scheduling: ${error.message}` }] }
    }
  }

  if (name === "cancel_campaign") {
    const { campaign_id, shop } = args as any
    try {
      const result = await makeApiCall("/cancel-campaign", "POST", { campaignId: campaign_id }, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error cancelling: ${error.message}` }] }
    }
  }

  if (name === "delete_campaign") {
    const { campaign_id, shop } = args as any
    try {
      // DELETE request usually takes body or query params depending on implementation
      // Doc says: Request Body: { campaignId: "..." }
      // makeApiCall handles DELETE with body correctly now
      const result = await makeApiCall("/delete-campaign", "DELETE", { campaignId: campaign_id }, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error deleting: ${error.message}` }] }
    }
  }

  if (name === "get_campaign_performance") {
    const { campaign_id, shop } = args as any
    try {
      // Parallel fetch of ROI, CTR, Cost
      const [roiRes, ctrRes, costRes, recipientsRes] = await Promise.all([
        makeApiCall(`/get-campaign-roi/${campaign_id}`, "GET", undefined, shop).catch(e => ({ error: e.message })),
        makeApiCall(`/get-campaign-ctr/${campaign_id}`, "GET", undefined, shop).catch(e => ({ error: e.message })),
        makeApiCall(`/get-campaign-cost/${campaign_id}`, "GET", undefined, shop).catch(e => ({ error: e.message })),
        makeApiCall(`/get-recipients-count-from-campaign-id/${campaign_id}`, "GET", undefined, shop).catch(e => ({ error: e.message }))
      ])

      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            campaign_id,
            roi_stats: roiRes,
            ctr_stats: ctrRes,
            cost_stats: costRes,
            recipient_stats: recipientsRes
          }, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error fetching performance: ${error.message}` }] }
    }
  }

  if (name === "list_segments") {
    const { shop } = args as any
    try {
      // Use get-all-segment-names for value-list retrieval
      const result = await makeApiCall("/get-all-segment-names", "GET", undefined, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error listing segments: ${error.message}` }] }
    }
  }

  // ──── Campaign Plan Handlers ─────────────────────────────────────────────

  if (name === "create_plan") {
    const { shop, name: planName, period, period_start, period_end, industry, goals, campaigns } = args as any
    try {
      const input: CreatePlanInput = {
        shop,
        name: planName,
        period: period as PlanPeriod,
        period_start,
        period_end,
        industry,
        goals,
        campaigns,
      }
      const plan = await createPlan(input)
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            success: true,
            plan_id: plan.plan_id,
            name: plan.name,
            total_campaigns: plan.summary.total,
            period: plan.period,
            created_at: plan.created_at,
          }, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error creating plan: ${error.message}` }] }
    }
  }

  if (name === "update_plan_campaign") {
    const { plan_id, shop, campaign_index, campaign_id, status, error: slotError } = args as any
    try {
      const result = await updatePlanCampaign(
        plan_id,
        shop,
        campaign_index,
        campaign_id ?? null,
        status as CampaignSlotStatus,
        slotError,
      )
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error updating plan campaign: ${error.message}` }] }
    }
  }

  if (name === "get_plan") {
    const { plan_id, shop } = args as any
    try {
      const plan = await getPlan(plan_id, shop)
      if (!plan) {
        return { isError: true, content: [{ type: "text", text: `Plan not found: ${plan_id}` }] }
      }
      return {
        content: [{
          type: "text",
          text: JSON.stringify(plan, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error getting plan: ${error.message}` }] }
    }
  }

  if (name === "list_plans") {
    const { shop, status } = args as any
    try {
      const plans = await listPlans(shop, status)
      return {
        content: [{
          type: "text",
          text: JSON.stringify({ plans, count: plans.length }, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error listing plans: ${error.message}` }] }
    }
  }

  // ──── Shopify Store Info Handlers ─────────────────────────────────────────

  if (name === "get_shop_info") {
    const { shop } = args as any
    try {
      const result = await makeApiCall("/shopify-store/info", "GET", undefined, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error getting shop info: ${error.message}` }] }
    }
  }

  if (name === "get_products") {
    const { shop, filter = "all", limit = 50 } = args as any
    try {
      const queryParams = new URLSearchParams({ filter, limit: limit.toString() })
      const result = await makeApiCall(`/shopify-store/products?${queryParams.toString()}`, "GET", undefined, shop)
      return {
        content: [{
          type: "text",
          text: JSON.stringify(result, null, 2)
        }]
      }
    } catch (error: any) {
      return { isError: true, content: [{ type: "text", text: `Error getting products: ${error.message}` }] }
    }
  }

  throw new Error(`Unknown tool: ${name}`)
})

// Run server
async function main() {
  console.error(`Campaign DB (SMS App Integration) Server running...`)
  console.error(`Configured SMS App API URL: ${API_BASE_URL}`)
  const transport = new StdioServerTransport()
  await server.connect(transport)
}

main().catch(console.error)
