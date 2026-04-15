import express from 'express';
import { createServer as createHttpServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import cors from 'cors';
import { setupWebSocket } from './websocket/handlers';
import { connectMongoDB } from './services/mongodb';
import { logger } from './utils/logger';
import { ConversationManager } from './services/conversation-manager';
import mongoose from 'mongoose';
import { getPlan, listPlans, createPlan, cancelPlan, deletePlan } from './services/plan-store';
import { SessionLogger } from './services/session-logger';

const PORT = process.env.PORT || 8008;
const SMS_APP_API_URL = process.env.SMS_APP_API_URL || 'http://localhost:3000';

/**
 * Cancel a scheduled campaign via sms-app API.
 */
async function cancelScheduledCampaign(campaignId: string, shop: string): Promise<void> {
  const res = await fetch(`${SMS_APP_API_URL}/cancel-campaign`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ campaignId, shop }),
  });
  if (!res.ok) {
    throw new Error(`cancel-campaign API returned ${res.status}`);
  }
}

/**
 * Delete a campaign via sms-app API.
 */
async function deleteScheduledCampaign(campaignId: string, shop: string): Promise<void> {
  const res = await fetch(`${SMS_APP_API_URL}/delete-campaign`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ campaignId, shop }),
  });
  if (!res.ok) {
    throw new Error(`delete-campaign API returned ${res.status}`);
  }
}

export async function createServer() {
  // Connect MongoDB for session logging (non-blocking)
  await connectMongoDB();

  const app = express();
  const httpServer = createHttpServer(app);

  // Middleware
  const allowedOrigins = process.env.ALLOWED_ORIGINS?.split(',').map(o => o.trim()).filter(Boolean) || []

  app.use(cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (mobile apps, curl, etc.)
      if (!origin) return callback(null, true)
      // If no whitelist configured, reflect the requesting origin (needed for credentials: true)
      if (allowedOrigins.length === 0) return callback(null, true)
      if (allowedOrigins.includes(origin)) return callback(null, true)
      // Unknown origin — still allow but without credentials (or reject)
      callback(null, true)
    },
    credentials: true
  }));
  app.use(express.json());

  // Setup Socket.io
  const io = new SocketIOServer(httpServer, {
    path: '/ws',
    cors: {
      origin: process.env.ALLOWED_ORIGINS?.split(',') || '*',
      credentials: true
    },
    pingTimeout: 60000,
    pingInterval: 25000,
    transports: ['websocket', 'polling']
  });

  // Setup WebSocket handlers
  setupWebSocket(io);

  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({
      status: 'ok',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      environment: process.env.NODE_ENV
    });
  });

  // Metrics endpoint
  app.get('/metrics', (req, res) => {
    res.json({
      connections: io.engine.clientsCount,
      memory: process.memoryUsage(),
      uptime: process.uptime(),
      timestamp: new Date().toISOString()
    });
  });

  // Root endpoint
  app.get('/', (req, res) => {
    res.json({
      name: 'AI Service',
      version: '1.0.0',
      status: 'running',
      endpoints: {
        websocket: '/ws',
        health: '/health',
        metrics: '/metrics'
      }
    });
  });

  /**
   * Core function: run a single campaign generation through OpenCode agent.
   * Used by both /internal/generate-plan-campaign (scheduler) and /plan/:planId/generate (parallel).
   */
  async function runSingleCampaignGeneration(input: {
    shop: string
    userId: string
    plan_id: string
    campaign_index: number
    message: string
  }): Promise<{ success: boolean; result?: any; error?: string }> {
    const { shop, userId, plan_id, campaign_index, message } = input

    logger.info(`[campaign-gen] Starting slot=${campaign_index}, plan=${plan_id}`)

    const conversationManager = new ConversationManager()

    try {
      const context = await conversationManager.startConversation(shop, userId)

      const sLogger = new SessionLogger(
        context.conversationId,
        shop,
        userId,
        context.opencodeSessionId,
      )

      sLogger.startTurn(message)

      const result = await new Promise<{
        fullText: string
        totalCost: number
        totalTokens: number
        toolCalls: string[]
      }>((resolve, reject) => {
        const callbacks = {
          onStepFinish: (data: any) => {
            sLogger.addStepData(data.cost, data.tokens)
          },
          onSubAgentStart: (agentType: string, description: string) => {
            sLogger.startSubAgent(agentType, description, '')
          },
          onSubAgentComplete: (agentType: string, result: any) => {
            sLogger.completeSubAgent(agentType, result)
          },
          onComplete: (data: any) => resolve({
            fullText: data.fullText || '',
            totalCost: data.totalCost || 0,
            totalTokens: data.totalTokens || 0,
            toolCalls: data.toolCalls || [],
          }),
          onError: (err: Error) => reject(err),
          onTextToken: () => {},
          onTextUpdate: (fullText: string) => {
            sLogger.accumulateText(fullText)
          },
          onReasoningToken: (delta: string) => {
            sLogger.accumulateReasoning(delta)
          },
          onReasoningUpdate: () => {},
          onToolStart: (tool: string, input: any) => {
            if (tool !== 'task') {
              sLogger.addToolCall(tool, input)
            }
          },
          onToolRunning: (tool: string, state: any) => {
            if (tool !== 'task' && state?.input) {
              sLogger.updateToolCallInput(tool, state.input)
            }
            if (state?.input?.subagent_type) {
              sLogger.startSubAgent(
                state.input.subagent_type,
                state.input.description || '',
                state.input.prompt || '',
              )
            }
          },
          onToolComplete: (tool: string, output: any) => {
            if (tool !== 'task') {
              sLogger.updateToolCall(tool, output, 'completed')
            }
            if (tool === 'char_counter' && output) {
              sLogger.setSmsInfo(output)
            }
          },
          onSubAgentReasoning: (agentType: string, delta: string) => {
            sLogger.accumulateSubAgentReasoning(agentType, delta)
          },
          onSubAgentText: (agentType: string, delta: string) => {
            sLogger.accumulateSubAgentText(agentType, delta)
          },
          onSubAgentToolStart: (agentType: string, tool: string, input: any) => {
            sLogger.addSubAgentToolCall(agentType, tool, input)
          },
          onSubAgentToolComplete: (agentType: string, tool: string, output: any) => {
            sLogger.completeSubAgentToolCall(agentType, tool, output)
          },
          onQuestion: () => {},
          onStepStart: () => {},
          onBusy: () => {},
          onIdle: () => {},
        }

        conversationManager.processMessage(context.conversationId, message, callbacks)
          .catch(reject)
      })

      logger.info(`[campaign-gen] Slot=${campaign_index} complete: cost=$${result.totalCost.toFixed(6)}, tokens=${result.totalTokens}`)

      // Flush turn to MongoDB + Langfuse (fire-and-forget)
      sLogger.completeTurn(
        result.fullText,
        '',
        result.totalCost,
        result.totalTokens,
      ).catch(() => {})

      // Cleanup
      await conversationManager.deleteConversation(context.conversationId)

      return { success: true, result }

    } catch (err: any) {
      logger.error(`[campaign-gen] Slot=${campaign_index} failed: ${err.message}`)
      return { success: false, error: err.message }
    }
  }

  // Internal endpoint: triggered by plan-executor scheduler
  // Delegates to the shared runSingleCampaignGeneration function
  app.post('/internal/generate-plan-campaign', async (req, res) => {
    const { shop, userId, plan_id, campaign_index, message } = req.body as {
      shop: string
      userId: string
      plan_id: string
      campaign_index: number
      message: string
    }

    if (!shop || !userId || !plan_id || campaign_index === undefined || !message) {
      res.status(400).json({ error: 'Missing required fields: shop, userId, plan_id, campaign_index, message' })
      return
    }

    const outcome = await runSingleCampaignGeneration({ shop, userId, plan_id, campaign_index, message })

    if (outcome.success) {
      res.json({ success: true, result: outcome.result })
    } else {
      res.status(500).json({
        error: 'Generation failed',
        message: outcome.error,
        plan_id,
        campaign_index,
      })
    }
  })

  // ──── Plan API Endpoints ──────────────────────────────────────────────────

  /**
   * Helper: run a message through the agent and wait for completion
   */
  async function runAgentMessage(shop: string, userId: string, message: string) {
    const conversationManager = new ConversationManager()
    const context = await conversationManager.startConversation(shop, userId)

    const sLogger = new SessionLogger(
      context.conversationId,
      shop,
      userId,
      context.opencodeSessionId,
    )

    sLogger.startTurn(message)

    const result = await new Promise<{
      fullText: string
      totalCost: number
      totalTokens: number
      toolCalls: string[]
    }>((resolve, reject) => {
      const callbacks = {
        onStepFinish: (data: any) => {
          sLogger.addStepData(data.cost, data.tokens)
        },
        onSubAgentStart: (agentType: string, description: string) => {
          sLogger.startSubAgent(agentType, description, '')
        },
        onSubAgentComplete: (agentType: string, result: any) => {
          sLogger.completeSubAgent(agentType, result)
        },
        onComplete: (data: any) => resolve({
          fullText: data.fullText || '',
          totalCost: data.totalCost || 0,
          totalTokens: data.totalTokens || 0,
          toolCalls: data.toolCalls || [],
        }),
        onError: (err: Error) => reject(err),
        onTextToken: () => {},
        onTextUpdate: (fullText: string) => {
          sLogger.accumulateText(fullText)
        },
        onReasoningToken: (delta: string) => {
          sLogger.accumulateReasoning(delta)
        },
        onReasoningUpdate: () => {},
        onToolStart: (tool: string, input: any) => {
          if (tool !== 'task') {
            sLogger.addToolCall(tool, input)
          }
        },
        onToolRunning: (tool: string, state: any) => {
          if (tool !== 'task' && state?.input) {
            sLogger.updateToolCallInput(tool, state.input)
          }
          if (state?.input?.subagent_type) {
            sLogger.startSubAgent(
              state.input.subagent_type,
              state.input.description || '',
              state.input.prompt || '',
            )
          }
        },
        onToolComplete: (tool: string, output: any) => {
          if (tool !== 'task') {
            sLogger.updateToolCall(tool, output, 'completed')
          }
          if (tool === 'char_counter' && output) {
            sLogger.setSmsInfo(output)
          }
        },
        onSubAgentReasoning: (agentType: string, delta: string) => {
          sLogger.accumulateSubAgentReasoning(agentType, delta)
        },
        onSubAgentText: (agentType: string, delta: string) => {
          sLogger.accumulateSubAgentText(agentType, delta)
        },
        onSubAgentToolStart: (agentType: string, tool: string, input: any) => {
          sLogger.addSubAgentToolCall(agentType, tool, input)
        },
        onSubAgentToolComplete: (agentType: string, tool: string, output: any) => {
          sLogger.completeSubAgentToolCall(agentType, tool, output)
        },
        onQuestion: () => {},
        onStepStart: () => {},
        onBusy: () => {},
        onIdle: () => {},
      }

      conversationManager.processMessage(context.conversationId, message, callbacks)
        .catch(reject)
    })

    // Flush turn to MongoDB + Langfuse (fire-and-forget)
    sLogger.completeTurn(
      result.fullText,
      '',
      result.totalCost,
      result.totalTokens,
    ).catch(() => {})

    await conversationManager.deleteConversation(context.conversationId)
    return { result, conversationId: context.conversationId }
  }

  /**
   * POST /plan/create-async
   * Create a campaign plan asynchronously. Returns plan_id immediately,
   * agent designs calendar in background. Frontend polls GET /plan/:planId.
   */
  app.post('/plan/create-async', async (req, res) => {
    const { shop, userId, period, period_start, period_end, segment, goals } = req.body as {
      shop: string
      userId: string
      period: string
      period_start?: string
      segment?: string
      goals?: string
    }

    if (!shop || !userId || !period) {
      res.status(400).json({ error: 'Missing required fields: shop, userId, period' })
      return
    }

    const validPeriods = ['week', 'month', 'quarter', 'year']
    if (!validPeriods.includes(period)) {
      res.status(400).json({ error: `Invalid period. Must be one of: ${validPeriods.join(', ')}` })
      return
    }

    // Create a placeholder plan immediately
    const now = new Date().toISOString()
    const placeholderPlan = await createPlan({
      shop,
      name: `${period} campaign plan (generating...)`,
      period,
      period_start: period_start || '',
      period_end: period_end || '',
      industry: 'pending',
      goals: goals || null,
      campaigns: [],
    })

    // Update status to "generating" so frontend knows it's in progress
    await mongoose.connection.db.collection('campaign_plans').updateOne(
      { plan_id: placeholderPlan.plan_id },
      { $set: { status: 'generating', updated_at: now } },
    )

    logger.info(`[plan-api] Async plan created: ${placeholderPlan.plan_id}, starting background generation`)

    // Return immediately
    res.json({
      success: true,
      plan_id: placeholderPlan.plan_id,
      plan: { ...placeholderPlan, status: 'generating' },
    })

    // Run agent in background (don't await)
    ;(async () => {
      try {
        const parts: string[] = [`Create an SMS plan for next ${period}`]
        if (period_start) parts.push(`starting ${period_start}`)
        if (period_end) parts.push(`ending ${period_end}`)
        if (segment) parts.push(`for ${segment} segment`)
        if (goals) parts.push(`Goals: ${goals}`)
        const message = parts.join(', ') + '. Only design the campaign calendar, do NOT generate any campaign messages or run the full pipeline. Return the calendar as a JSON block so it can be saved.'

        const { result } = await runAgentMessage(shop, userId, message)

        // Try to parse plan data from agent response
        let planData: any = null

        // Strategy 1: Find plan-builder sub-agent task output
        const taskCalls = (result.toolCalls as any[])?.filter(
          (tc: any) => tc.tool === 'task' && tc.state?.input?.subagent_type === 'plan-builder'
        )
        for (const tc of taskCalls || []) {
          const output = tc.state?.output
          if (output) {
            try {
              const parsed = typeof output === 'string' ? JSON.parse(output) : output
              if (parsed.campaigns && Array.isArray(parsed.campaigns)) {
                planData = parsed
                break
              }
            } catch { /* not JSON */ }
          }
        }

        // Strategy 2: Extract JSON block from agent text
        if (!planData) {
          const jsonMatch = result.fullText.match(/```json\s*([\s\S]*?)```/)
          if (jsonMatch) {
            try {
              const parsed = JSON.parse(jsonMatch[1])
              if (parsed.campaigns) planData = parsed
            } catch { /* not valid JSON */ }
          }
        }

        // Strategy 3: Agent may have called campaign-db_create_plan itself
        const agentCreateCall = (result.toolCalls as any[])?.find(
          (tc: any) => tc.tool === 'campaign-db_create_plan'
        )
        if (!planData && agentCreateCall?.state?.output) {
          try {
            const output = typeof agentCreateCall.state.output === 'string'
              ? JSON.parse(agentCreateCall.state.output)
              : agentCreateCall.state.output
            if (output.campaigns) planData = output
          } catch { /* ignore */ }
        }

        if (!planData) {
          logger.error(`[plan-api] Async plan ${placeholderPlan.plan_id}: could not parse plan data`)
          await mongoose.connection.db.collection('campaign_plans').updateOne(
            { plan_id: placeholderPlan.plan_id },
            { $set: { status: 'failed', updated_at: new Date().toISOString() } },
          )
          return
        }

        // Update the placeholder plan with real data
        const campaigns = (planData.campaigns || []).map((c: any, i: number) => ({
          index: c.index ?? i,
          campaign_id: null,
          status: 'pending_generation',
          campaign_type: c.campaign_type || '',
          offer_theme: c.offer_theme || c.offer_direction || '',
          segment_name: c.target_segment_name || c.segment_name || 'All Subscribers',
          segment_id: c.target_segment_id || c.segment_id || 'unknown',
          suggested_send_date: c.suggested_send_day || c.suggested_send_date || '',
          priority: c.priority || 'medium',
          rationale: c.rationale || null,
          updated_at: new Date().toISOString(),
        }))

        const totalCampaigns = campaigns.length
        await mongoose.connection.db.collection('campaign_plans').updateOne(
          { plan_id: placeholderPlan.plan_id },
          {
            $set: {
              name: planData.plan_name || `${period} campaign plan`,
              industry: planData.industry || 'other',
              campaigns,
              status: 'active',
              summary: { total: totalCampaigns, created: 0, pending: totalCampaigns, failed: 0 },
              updated_at: new Date().toISOString(),
            },
          },
        )

        logger.info(`[plan-api] Async plan ${placeholderPlan.plan_id} completed: ${totalCampaigns} campaigns`)
      } catch (err: any) {
        logger.error(`[plan-api] Async plan ${placeholderPlan.plan_id} failed: ${err.message}`)
        await mongoose.connection.db.collection('campaign_plans').updateOne(
          { plan_id: placeholderPlan.plan_id },
          { $set: { status: 'failed', updated_at: new Date().toISOString() } },
        )
      }
    })()
  })

  /**
   * POST /plan/create
   * Create a campaign plan. Agent designs calendar, backend saves to MongoDB.
   * NOTE: This is synchronous and may timeout behind Cloudflare. Use /plan/create-async instead.
   */
  app.post('/plan/create', async (req, res) => {
    const { shop, userId, period, period_start, period_end, segment, goals } = req.body as {
      shop: string
      userId: string
      period: string
      period_start?: string
      period_end?: string
      segment?: string
      goals?: string
    }

    if (!shop || !userId || !period) {
      res.status(400).json({ error: 'Missing required fields: shop, userId, period' })
      return
    }

    const validPeriods = ['week', 'month', 'quarter', 'year']
    if (!validPeriods.includes(period)) {
      res.status(400).json({ error: `Invalid period. Must be one of: ${validPeriods.join(', ')}` })
      return
    }

    // Build natural language prompt — no industry (agent infers from products)
    const parts: string[] = [`Create an SMS plan for next ${period}`]
    if (period_start) parts.push(`starting ${period_start}`)
    if (period_end) parts.push(`ending ${period_end}`)
    if (segment) parts.push(`for ${segment} segment`)
    if (goals) parts.push(`Goals: ${goals}`)
    // Agent only designs calendar — backend handles saving
    const message = parts.join(', ') + '. Only design the campaign calendar, do NOT generate any campaign messages or run the full pipeline. Return the calendar as a JSON block so it can be saved.'

    logger.info(`[plan-api] Creating plan: shop=${shop}, period=${period}`)

    try {
      const { result, conversationId } = await runAgentMessage(shop, userId, message)

      // Try to parse plan data from plan-builder sub-agent output
      let planData: any = null

      // Strategy 1: Find plan-builder sub-agent task output in toolCalls
      const taskCalls = (result.toolCalls as any[])?.filter(
        (tc: any) => tc.tool === 'task' && tc.state?.input?.subagent_type === 'plan-builder'
      )
      for (const tc of taskCalls || []) {
        const output = tc.state?.output
        if (output) {
          try {
            const parsed = typeof output === 'string' ? JSON.parse(output) : output
            if (parsed.campaigns && Array.isArray(parsed.campaigns)) {
              planData = parsed
              break
            }
          } catch { /* not JSON, try next */ }
        }
      }

      // Strategy 2: Extract JSON block from agent text response
      if (!planData) {
        const jsonMatch = result.fullText.match(/```json\s*([\s\S]*?)```/)
        if (jsonMatch) {
          try {
            const parsed = JSON.parse(jsonMatch[1])
            if (parsed.campaigns) planData = parsed
          } catch { /* not valid JSON */ }
        }
      }

      // Strategy 3: Agent may have called campaign-db_create_plan itself
      const agentCreateCall = (result.toolCalls as any[])?.find(
        (tc: any) => tc.tool === 'campaign-db_create_plan'
      )
      if (agentCreateCall?.state?.output) {
        try {
          const output = typeof agentCreateCall.state.output === 'string'
            ? JSON.parse(agentCreateCall.state.output)
            : agentCreateCall.state.output
          if (output.plan_id) {
            // Agent already saved — fetch from DB
            const existingPlan = await getPlan(output.plan_id, shop)
            if (existingPlan) {
              res.json({
                success: true,
                plan_id: output.plan_id,
                plan: existingPlan,
                conversationId,
                agentResponse: result.fullText,
                cost: result.totalCost,
                tokens: result.totalTokens,
              })
              return
            }
          }
        } catch { /* ignore parse errors */ }
      }

      if (!planData) {
        logger.error('[plan-api] Could not parse plan data from agent response')
        res.status(422).json({
          error: 'Could not parse plan calendar from agent response',
          agentResponse: result.fullText,
          cost: result.totalCost,
          tokens: result.totalTokens,
        })
        return
      }

      // Save plan directly to MongoDB
      const plan = await createPlan({
        shop,
        name: planData.plan_name || `${period} campaign plan`,
        period,
        period_start: planData.period_start || period_start || '',
        period_end: planData.period_end || period_end || '',
        industry: planData.industry || 'other',
        goals,
        campaigns: planData.campaigns,
      })

      res.json({
        success: true,
        plan_id: plan.plan_id,
        plan,
        conversationId,
        agentResponse: result.fullText,
        cost: result.totalCost,
        tokens: result.totalTokens,
      })
    } catch (err: any) {
      logger.error(`[plan-api] Create plan failed: ${err.message}`)
      res.status(500).json({ error: 'Plan creation failed', message: err.message })
    }
  })

  /**
   * POST /plan/:planId/generate
   * Approve and generate all campaigns in a plan — runs campaigns in PARALLEL.
   * Each campaign gets its own OpenCode session via /internal/generate-plan-campaign,
   * so 5 campaigns run concurrently instead of sequentially (~6 min vs ~25 min).
   */
  app.post('/plan/:planId/generate', async (req, res) => {
    const { planId } = req.params
    const { shop, userId } = req.body as { shop: string; userId: string }

    if (!shop || !userId) {
      res.status(400).json({ error: 'Missing required fields: shop, userId' })
      return
    }

    // Check plan exists
    const plan = await getPlan(planId, shop)
    if (!plan) {
      res.status(404).json({ error: 'Plan not found', plan_id: planId })
      return
    }

    if (plan.status !== 'active') {
      res.status(400).json({ error: `Plan status is '${plan.status}', must be 'active' to generate` })
      return
    }

    const pendingSlots = (plan.campaigns as any[])?.filter((c: any) => c.status === 'pending_generation') || []
    if (pendingSlots.length === 0) {
      res.status(400).json({ error: 'No pending campaigns to generate', plan_id: planId })
      return
    }

    logger.info(`[plan-api] Generating ${pendingSlots.length} campaigns in PARALLEL for plan=${planId}`)

    // Mark all slots as "generating" immediately
    const db = mongoose.connection.db!
    const collection = db.collection('campaign_plans')
    for (const slot of pendingSlots) {
      await collection.updateOne(
        { plan_id: planId },
        {
          $set: {
            [`campaigns.${slot.index}.status`]: 'generating',
            [`campaigns.${slot.index}.updated_at`]: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        },
      )
    }

    // Fire all campaigns in parallel via the shared generation function
    const results = await Promise.allSettled(
      pendingSlots.map((slot: any) => {
        const message = `[Plan Generation]

Create and schedule an SMS campaign based on the approved plan:

- **Plan ID**: ${planId}
- **Campaign index**: ${slot.index}
- **Campaign type**: ${slot.campaign_type}
- **Offer theme**: ${slot.offer_theme}
- **Segment**: ${slot.segment_name} (ID: ${slot.segment_id})
- **Scheduled send date**: ${slot.suggested_send_date}
- **Industry**: ${plan.industry}
- **Priority**: ${slot.priority}
${slot.rationale ? `- **Rationale**: ${slot.rationale}` : ''}

Create and schedule this campaign. Once done, call campaign-db_update_plan_campaign to update the status in the plan.`

        return runSingleCampaignGeneration({
          shop,
          userId,
          plan_id: planId,
          campaign_index: slot.index,
          message,
        })
      })
    )

    // Tally results
    let created = 0
    let failed = 0
    for (let i = 0; i < results.length; i++) {
      const r = results[i]
      if (r.status === 'fulfilled') {
        created++
      } else {
        failed++
        const slot = pendingSlots[i]
        const errMsg = r.status === 'rejected' ? (r.reason?.message || String(r.reason)) : 'Unknown error'
        logger.error(`[plan-api] Slot ${slot.index} failed: ${errMsg}`)
        // Mark as failed in DB
        await collection.updateOne(
          { plan_id: planId },
          {
            $set: {
              [`campaigns.${slot.index}.status`]: 'failed',
              [`campaigns.${slot.index}.error`]: errMsg,
              [`campaigns.${slot.index}.updated_at`]: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          },
        )
      }
    }

    // Update plan summary
    await collection.updateOne(
      { plan_id: planId },
      {
        $set: {
          'summary.created': created,
          'summary.failed': failed,
          'summary.pending': 0,
          updated_at: new Date().toISOString(),
        },
      },
    )

    // Fetch updated plan
    const updatedPlan = await getPlan(planId, shop)

    res.json({
      success: true,
      plan_id: planId,
      campaigns: updatedPlan?.campaigns || [],
      summary: {
        created,
        failed,
        total: pendingSlots.length,
      },
    })
  })

  /**
   * PATCH /plan/:planId/cancel
   * Cancel an active plan and stop all scheduled campaigns.
   */
  app.patch('/plan/:planId/cancel', async (req, res) => {
    const { planId } = req.params
    const { shop } = req.body as { shop: string }

    if (!shop) {
      res.status(400).json({ error: 'Missing required field: shop' })
      return
    }

    const result = await cancelPlan(planId, shop)
    if (!result) {
      res.status(404).json({ error: 'Active plan not found or already cancelled', plan_id: planId })
      return
    }

    // Cancel scheduled campaigns via sms-app API
    let cancelledCount = 0
    for (const campaignId of result.campaignIds) {
      try {
        await cancelScheduledCampaign(campaignId, shop)
        cancelledCount++
      } catch (err: any) {
        logger.warn(`[plan-api] Failed to cancel campaign ${campaignId}: ${err.message}`)
      }
    }

    res.json({
      success: true,
      plan_id: planId,
      status: 'cancelled',
      cancelled_campaigns: cancelledCount,
      total_campaigns: result.campaignIds.length,
    })
  })

  /**
   * DELETE /plan/:planId
   * Delete a plan (any status) and remove all associated campaigns.
   */
  app.delete('/plan/:planId', async (req, res) => {
    const { planId } = req.params
    const { shop } = req.body as { shop: string }

    if (!shop) {
      res.status(400).json({ error: 'Missing required field: shop' })
      return
    }

    const result = await deletePlan(planId, shop)
    if (!result) {
      res.status(404).json({ error: 'Plan not found', plan_id: planId })
      return
    }

    // Delete campaigns via sms-app API
    let deletedCount = 0
    for (const campaignId of result.campaignIds) {
      try {
        await deleteScheduledCampaign(campaignId, shop)
        deletedCount++
      } catch (err: any) {
        logger.warn(`[plan-api] Failed to delete campaign ${campaignId}: ${err.message}`)
      }
    }

    res.json({
      success: true,
      plan_id: planId,
      deleted_campaigns: deletedCount,
      total_campaigns: result.campaignIds.length,
    })
  })

  /**
   * GET /plan/:planId
   * Get plan status from MongoDB directly (no agent call).
   */
  app.get('/plan/:planId', async (req, res) => {
    const { planId } = req.params
    const shop = req.query.shop as string

    if (!shop) {
      res.status(400).json({ error: 'Missing query param: shop' })
      return
    }

    const plan = await getPlan(planId, shop)
    if (!plan) {
      res.status(404).json({ error: 'Plan not found', plan_id: planId })
      return
    }

    res.json({ success: true, plan })
  })

  /**
   * GET /plans
   * List all plans for a shop.
   */
  app.get('/plans', async (req, res) => {
    const shop = req.query.shop as string
    const status = req.query.status as string | undefined

    if (!shop) {
      res.status(400).json({ error: 'Missing query param: shop' })
      return
    }

    const plans = await listPlans(shop, status)
    res.json({ success: true, count: plans.length, plans })
  })

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({
      error: 'Not Found',
      path: req.path
    });
  });

  // Error handler
  app.use((err: any, req: express.Request, res: express.Response, next: express.NextFunction) => {
    logger.error('Express error:', err);
    res.status(500).json({
      error: 'Internal Server Error',
      message: process.env.NODE_ENV === 'development' ? err.message : undefined
    });
  });

  logger.info('✅ Express server configured');

  return httpServer;
}
