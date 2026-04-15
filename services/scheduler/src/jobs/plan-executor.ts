/**
 * Plan Executor Job
 *
 * Runs daily at 6AM UTC. Finds campaign_plan slots with status "pending_generation"
 * whose suggested_send_date is within 14 days, then triggers generation via
 * the backend WebSocket API (OpenCode).
 *
 * This handles quarter/year plans where campaigns are deferred and generated
 * rolling 14 days before their scheduled send date.
 */

import { BaseJob } from './base-job.js'
import { getDevDb } from '../db/connection.js'
import { createModuleLogger } from '../utils/logger.js'

const log = createModuleLogger('plan-executor')

const BACKEND_WS_URL = process.env.BACKEND_URL || 'http://localhost:8008'
const DAYS_AHEAD = parseInt(process.env.PLAN_EXECUTOR_DAYS_AHEAD || '14', 10)
const INTERNAL_USER_ID = 'scheduler-plan-executor'

interface CampaignSlot {
  index: number
  campaign_id: string | null
  status: string
  campaign_type: string
  offer_theme: string
  segment_name: string
  segment_id: string
  suggested_send_date: string
  priority: string
  rationale?: string
}

interface CampaignPlan {
  plan_id: string
  shop: string
  name: string
  period: string
  industry: string
  goals?: string
  campaigns: CampaignSlot[]
}

export class PlanExecutorJob extends BaseJob {
  readonly jobName = 'plan-executor'

  protected async execute(): Promise<Record<string, number>> {
    const db = await getDevDb()
    const plansCol = db.collection<CampaignPlan>('campaign_plans')

    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() + DAYS_AHEAD)

    // Find all active plans with pending slots
    const plans = await plansCol.find({
      status: 'active',
      'campaigns.status': 'pending_generation',
    }).toArray()

    log.info(`Found ${plans.length} active plans to check`)

    let triggered = 0
    let skipped = 0
    let errors = 0

    for (const plan of plans) {
      for (const slot of plan.campaigns) {
        if (slot.status !== 'pending_generation') continue

        const sendDate = new Date(slot.suggested_send_date)
        if (sendDate > cutoff) {
          skipped++
          continue
        }

        log.info(`Triggering generation for plan=${plan.plan_id}, slot=${slot.index}: ${slot.offer_theme}`)

        try {
          await this.triggerCampaignGeneration(plan, slot)

          // Mark as "generating" immediately
          await plansCol.updateOne(
            { plan_id: plan.plan_id },
            {
              $set: {
                [`campaigns.${slot.index}.status`]: 'generating',
                [`campaigns.${slot.index}.updated_at`]: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            },
          )

          triggered++
        } catch (err: any) {
          log.error(`Failed to trigger slot ${slot.index} of plan ${plan.plan_id}: ${err.message}`)

          await plansCol.updateOne(
            { plan_id: plan.plan_id },
            {
              $set: {
                [`campaigns.${slot.index}.status`]: 'failed',
                [`campaigns.${slot.index}.error`]: err.message,
                [`campaigns.${slot.index}.updated_at`]: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            },
          )

          errors++
        }
      }
    }

    log.info(`Plan executor complete: triggered=${triggered}, skipped=${skipped}, errors=${errors}`)
    return { triggered, skipped, errors, plans_checked: plans.length }
  }

  /**
   * Trigger campaign generation via the backend HTTP API
   * POSTs a structured generation request to the backend, which opens
   * an OpenCode session and runs the full pipeline.
   */
  private async triggerCampaignGeneration(plan: CampaignPlan, slot: CampaignSlot): Promise<void> {
    const message = this.buildGenerationPrompt(plan, slot)

    const response = await fetch(`${BACKEND_WS_URL}/internal/generate-plan-campaign`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        shop: plan.shop,
        userId: INTERNAL_USER_ID,
        plan_id: plan.plan_id,
        campaign_index: slot.index,
        message,
      }),
      signal: AbortSignal.timeout(300_000), // 5 min timeout per campaign
    })

    if (!response.ok) {
      const text = await response.text().catch(() => '')
      throw new Error(`Backend API error ${response.status}: ${text.slice(0, 200)}`)
    }
  }

  private buildGenerationPrompt(plan: CampaignPlan, slot: CampaignSlot): string {
    return `[Plan Executor - Auto Generation]

Create and schedule an SMS campaign based on the approved plan:

- **Plan ID**: ${plan.plan_id}
- **Campaign index**: ${slot.index}
- **Campaign type**: ${slot.campaign_type}
- **Offer theme**: ${slot.offer_theme}
- **Segment**: ${slot.segment_name} (ID: ${slot.segment_id})
- **Scheduled send date**: ${slot.suggested_send_date}
- **Industry**: ${plan.industry}
- **Priority**: ${slot.priority}
${slot.rationale ? `- **Rationale**: ${slot.rationale}` : ''}

Create and schedule this campaign. Once done, call campaign-db_update_plan_campaign to update the status in the plan.`
  }
}
