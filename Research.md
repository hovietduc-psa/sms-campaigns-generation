# Automated SMS Campaign Flow Generation System Design

## Introduction

Designing effective SMS marketing flows can be a complex task,
especially when marketers provide only a brief campaign idea. This
document outlines a system that leverages a Large Language Model (LLM)
to automatically generate high-quality SMS campaign flows from a simple
text description. The goal is to streamline campaign creation by
producing a complete JSON flow (for an SMS automation platform) that
adheres strictly to a predefined node schema. By using an LLM, the
system translates vague or detailed marketing intents into structured,
executable campaign workflows without manual intervention.

## System Requirements

**Key features and constraints of the system include:**

-   **Input:** A natural language **campaign description** (English
    only) provided via an API. Descriptions may range from short phrases
    (e.g. \"*boost VIP reorders*\") to longer directives (e.g.
    \"*nurture first-time buyers with abandoned cart recovery and
    personalized offers*\").
-   **Output:** A **JSON-based SMS campaign structure** that conforms to
    the FlowBuilder node schema (see *Node Schema and Flow Structure*
    below). The JSON will include an `initialStepID` and a list of fully
    fleshed-out `steps` (nodes), with all required fields and correct
    linkages between nodes. Each node (message, segment, delay, etc.)
    must have the proper fields and any child events (transitions) as
    defined by the schema.
-   **Flow Logic:** The LLM-generated flows should incorporate
    **logic-driven elements** (conditional branches, delays, splits) as
    appropriate. The system will **simulate customer data and behavior**
    for flow decisions -- for example, using mock customer properties or
    event conditions (like purchase history, cart activity, etc.) to
    branch the flow. This ensures even abstract campaign ideas result in
    actionable logic (e.g. differentiating VIP customers, detecting an
    abandoned cart event, etc.).
-   **No UI (API-Only):** The system is exposed as an API service. There
    is no manual editing or frontend flow builder involved. The LLM
    handles end-to-end generation of the JSON, which can then be
    reviewed by a user and executed by the SMS platform.
-   **Quality and Consistency:** The generated flow must be immediately
    usable. This means all node linkages must be valid (no broken
    references), required fields present, and content coherent. The LLM
    is instructed to follow the schema **strictly**, producing output
    that passes validation and follows best practices (e.g. including
    personalization placeholders like `{{first_name}}` where
    appropriate, using engaging but concise message text, etc.).

## Node Schema and Flow Structure

The system's output JSON follows the **FlowBuilder schema** provided in
the documentation. At a high level, the JSON has the form:

    {
      "initialStepID": "<id-of-first-node>",
      "steps": [ … ]
    }

-   **Initial Step:** `initialStepID` is the identifier of the first
    step/node in the flow. (The underlying platform implicitly has a
    **Start** trigger node, not included in `steps`, which leads into
    this initial step.) The LLM must choose an appropriate first node
    based on the campaign description (often a segment or message node).
-   **Steps Array:** `steps` is an array of node objects. Each node has
    a unique `"id"` and a `"type"` indicating its function. All required
    fields for that type must be present (even if some are empty or use
    default values). Nodes also include an `"events"` list defining
    outbound connections (transitions) from that node. Every
    `nextStepID` in an event should correspond to another node's `id` in
    the same `steps` array.

**Node Types:** The system supports all node types defined in the
schema, and the LLM will select the appropriate ones for the campaign
logic. Key node types (with their typical usage) include:

-   **Message Node:** Sends an SMS message to the user. It contains the
    message text content (and optionally an image or discount code). For
    example, `content`/`text` fields hold the SMS text, and fields like
    `discountType` or `imageUrl` can enrich the message. A Message
    node's events often include a **reply** event (if expecting user
    response, e.g. intent \"yes\" or \"buy\") and/or a **noreply** event
    (to handle no response within a time frame). These events lead to
    other nodes (e.g. a reply might lead to a purchase offer, and a
    no-reply might lead to a reminder message).
-   **Segment Node:** A branching logic node that splits the audience
    based on conditions. It evaluates customer data or behaviors. For
    example, a Segment node can check if a customer is tagged as VIP or
    if they performed an action like \"started_checkout\" in the last 7
    days. The node's `conditions` array holds one or more conditions
    (each condition can be based on an event, a customer property, etc.,
    as defined in the schema). The Segment node typically has two
    outgoing events of type **split**: an `"include"` branch (customers
    who meet the condition) and an `"exclude"` branch (those who do
    not). Each branch has its own `nextStepID` for the respective path.
-   **Delay Node:** Pauses the flow for a specified duration (e.g. wait
    2 hours or 3 days). The node includes a `time` value and `period`
    unit (Seconds, Minutes, Hours, Days). After the delay, a **default**
    event leads to the next step in the flow (continuing the sequence).
-   **Trigger/Action Nodes:** Specialized nodes like **Reply** or
    **NoReply** (for handling user responses or lack thereof),
    **Property** (to set customer properties), **Limit/RateLimit** (to
    prevent sending too many messages in a period), **Schedule** (to
    branch by date/time ranges), **Experiment** (A/B test branching),
    etc. In our current scope, the LLM will mainly use these if relevant
    to the campaign description (for example, an Experiment node if the
    user asked for a split test, or a Limit node if the flow should cap
    messages per user). Each of these nodes has a defined schema
    structure that the LLM will follow. *(For brevity, we focus on the
    most common nodes in examples, but the system can generate any node
    type as needed.)*
-   **Purchase Offer Node:** A node that presents the user's cart and
    prompts an instant purchase via SMS. Often used for abandoned cart
    recovery or expedited checkout. This node includes fields like
    `messageText` (e.g. \"Reply \'YES\' to buy:\\n\\nCart List\"), a
    `cartSource` (either \"manual\" with specified products or
    \"latest\" to use the customer's most recent cart), and optional
    discount settings. Its events usually include a **reply** event
    (intent \"yes\" to confirm purchase, leading to a Purchase node) and
    a **noreply** event (leading to a follow-up or ending if the user
    ignores the offer).
-   **Product Choice Node:** An interactive node that lists products
    (usually for cross-sell or personalized recommendations) and waits
    for the user to pick one to buy. It has a `messageText` (e.g.
    \"Reply to buy:\\n\\n{{Product List}}\") and a `productSelection`
    mode. The selection can be **automatic** (the system selects
    products based on popularity or personalization), or **manual** (the
    JSON includes a list of specific products to offer with IDs and
    labels). The events often include a **reply** event (intent \"buy\"
    to proceed with the chosen item's purchase) and a **noreply** event
    (if the user doesn't respond, leading to a reminder or end).
-   **Purchase Node:** Completes a purchase by charging the user's saved
    payment method or sending a checkout link. It usually comes at the
    end of a flow after a user agrees to buy. The Purchase node will use
    the cart from prior steps (`cartSource` can be \"latest\" to use
    whatever cart was built by a Purchase Offer or Product Choice). It
    has options like `sendReminderForNonPurchasers` (to automatically
    remind if the user fails to complete payment). In the flow JSON, a
    Purchase node simply leads to a final **End** node after execution.
-   **End Node:** Marks the termination of the flow. Every branch should
    eventually connect to an End node. The End node has no outgoing
    events and typically just a label \"End\".

Each node will include `"active": true` (since all steps in a newly
generated flow are active by default) and an empty `"parameters": {}`
object as placeholders for any future advanced settings. Ensuring
presence of these fields is part of strict compliance with the schema.

## High-Level Architecture

The system is composed of several components orchestrated to transform a
user's description into a validated JSON flow. Below is an outline of
the architecture:

-   **API Layer:** Exposes an HTTP endpoint (e.g. `POST /generateFlow`)
    to accept campaign description input and return the generated JSON.
    The API layer handles request validation (ensuring a description is
    provided) and formatting of responses. It does not implement
    business logic beyond routing the request to the LLM engine and
    returning the result.

-   **LLM Generation Engine:** The core component that interfaces with
    the Large Language Model (such as GPT-4 or another advanced model).
    This engine is responsible for constructing the prompt for the LLM,
    invoking the model, and post-processing its output. Key
    sub-components/steps include:

-   **Prompt Constructor:** Takes the campaign description and embeds it
    into a carefully designed prompt that includes instructions,
    context, and schema guidance. (Details of the prompt design are
    discussed in the next section.)

-   **LLM Invocation:** Sends the prompt to the LLM (which could be
    hosted via an external API or a fine-tuned model internally) and
    receives the raw output. This output is expected to be a JSON string
    representing the flow.

-   **Parsing & Post-processing:** Parses the LLM's output from text
    into a JSON object. Minor format corrections are applied if needed
    (for instance, fixing unescaped characters or ensuring proper JSON
    syntax if the LLM output was close to valid JSON but not perfect).

-   **Validation Module:** This module validates the JSON against the
    flow schema rules. It checks for structural correctness and logical
    consistency:

-   All required fields present in each node (e.g. a Message node must
    have `content`, a Segment node must have conditions, etc.).

-   Field values are of the correct type/format (e.g. `time` is a string
    number, `period` is one of the allowed strings, `id` fields are
    non-empty strings, etc.).

-   References between nodes are valid: every `nextStepID` in events
    refers to an existing node ID, and the `initialStepID` matches one
    of the step IDs.

-   Event types align with required additional fields (e.g. if `type` is
    \"reply\", then an `intent` (and ideally a `description`) is
    provided; if `type` is \"noreply\", an `after` delay object is
    provided; if `type` is \"split\", `label` and `action` are set
    appropriately, etc. ).

-   Unique IDs: It's verified that each node `id` and event `id` in the
    flow is unique to avoid conflicts. The LLM is prompted to create
    human-readable unique IDs (e.g. \"vip-offer\", \"end-node\") or
    UUID-like strings, but the validator will flag any duplicates or
    missing references.

If the Validation Module finds issues, the system can either
**auto-correct** them (for example, if a minor field is missing,
possibly have the LLM regenerate or fill a default) or return an error
back to the user for review. The design leans towards automation: in
many cases the LLM can be re-prompted with feedback about what was wrong
to produce a corrected output, without human intervention.

-   **(Optional) Data & Knowledge Base:** In the current design, the LLM
    relies on prompt instructions to \"simulate\" customer data (like
    assuming what a VIP means, or making up product examples). In future
    iterations, this component could connect to real data sources:
-   e.g. a product catalog API to fetch actual popular products or the
    specific items in a customer's abandoned cart,
-   or a customer profile service to get real segment conditions. In a
    fully automated context, the system might incorporate
    retrieval-augmented generation (RAG) where the LLM can call
    functions or search knowledge bases for dynamic data. For now,
    however, all such data is mocked in the LLM's output (using
    placeholders like generic product IDs or sample condition values).

All these components work together in a pipeline. For example, when a
request comes in with a campaign idea, the API passes it to the LLM
Engine, the engine builds a prompt (with embedded schema knowledge), the
LLM produces a draft flow, and then the Validation module checks it.
Finally, the API returns the JSON result. This architecture ensures that
the heavy lifting (creative generation of the flow logic and content) is
done by the LLM, while the deterministic parts (format and schema
correctness) are enforced by the system around it.

*(An architecture diagram could illustrate these components: the API
calling the LLM service, which in turn uses the schema context and
passes output to a validator, etc., before responding. For brevity, we
omit a diagram and describe the flow in text.)*

## Input and Output Specifications

**API Endpoint:** `POST /generateFlow` -- Accepts a JSON request and
returns a JSON response.

-   **Request Body:** A JSON object with the campaign description and
    optional parameters. For example:

```{=html}
<!-- -->
```
    {
      "campaignDescription": "boost VIP reorders"
    }

In the simplest form, only the `campaignDescription` (string) is
required. In the future, this could be extended with fields like
`language` (to support other languages), or flags for certain
preferences (e.g. no discounts, or a specific tone), but those are
outside the current scope.

-   **Response Body:** On success, the API returns a JSON object
    representing the flow. This will directly include the
    `initialStepID` and `steps` as top-level fields (as shown in
    previous sections). For example:

```{=html}
<!-- -->
```
    {
      "initialStepID": "start-message",
      "steps": [
         { "id": "start-message", "type": "message", ... },
         { ... },
         ...
      ]
    }

The response is essentially the flow definition that can be imported or
executed in the SMS marketing system. We ensure the output is properly
formatted as JSON (with the correct content types and encoding).

-   **Error Handling:** If the input is invalid (e.g. missing
    description or not a string) the API returns an error response (HTTP
    400 with a message). If the LLM generation fails or the output is
    not valid JSON even after retries, the API may return an error
    (HTTP 500) indicating the generation could not be completed. In
    practice, the system will try to avoid errors by employing
    validation and a second attempt to fix issues. For instance, if the
    LLM returns text that isn't parseable JSON, the engine might
    automatically attempt to correct formatting or re-prompt the model
    with a stricter instruction to only output JSON. The user is
    expected to review the final JSON (especially in early usage) but
    not to manually edit it -- the system's goal is that the JSON is
    ready for use as-is.

-   **Performance:** Each call involves an LLM query. The latency
    depends on the model (usually a few seconds). This is acceptable for
    an asynchronous campaign design task. Throughput considerations (if
    many campaigns are generated per hour) can be addressed by scaling
    the LLM service or caching results for identical inputs. Caching
    might not be very effective here since campaign descriptions are
    usually unique, but it's mentioned as a possible optimization for
    repeated
    requests[\[1\]](https://medium.com/@vi.ha.engr/the-architects-guide-to-llm-system-design-from-prompt-to-production-8be21ebac8bc#:~:text=Every%20call%20to%20an%20LLM,offs%20in%20complexity%20and%20effectiveness)[\[2\]](https://medium.com/@vi.ha.engr/the-architects-guide-to-llm-system-design-from-prompt-to-production-8be21ebac8bc#:~:text=1)
    (e.g. if the same user refines a campaign description multiple
    times, a semantic cache could reuse prior results).

## Generation Pipeline Design

The core challenge is guiding the LLM to produce a correct and effective
flow. The system uses prompt engineering and a structured pipeline to
achieve this:

1.  **Prompt Structure:** The LLM is prompted with a combination of
    instructions and context. We use a *system message* to set the stage
    and a *user message* containing the campaign description. The system
    prompt includes:
2.  **Role and Task Definition:** e.g. *\"You are an expert SMS
    marketing flow builder. You will receive a campaign description and
    you will output a JSON representing the campaign flow following a
    specific schema.\"* This clarifies that the model should act as a
    flow design assistant.
3.  **Schema and Format Guidelines:** A concise summary of the node
    schema rules is provided. This might include a list of node types
    and their required fields, the general JSON structure (initialStepID
    and steps array), and critical rules (like ensuring proper linking
    of `nextStepID`, including `active` and `parameters` in each node,
    etc.). The prompt will emphasize that **the output must be valid
    JSON** and contain no extraneous commentary. For example, the
    instructions will say something like: *\"Output only a JSON object
    with* `initialStepID` *and* `steps`*. Do not include any explanation
    or natural language outside of the JSON.\"* This is to guarantee the
    model doesn't drift into prose. We also remind the model of specific
    schema details (e.g. *\"Each message node must include* `content`
    *and an events array with at least one event.\"*).
4.  **Few-Shot Examples (if needed):** To improve reliability, we can
    include one or two examples within the prompt. For instance, a very
    simple campaign description paired with a small JSON flow as the
    correct output. This demonstrates the mapping from description to
    JSON. The examples would be drawn from known use cases (possibly
    from templates or the documentation's example). By seeing an
    example, the LLM can better infer the pattern of the output.
    However, since the output JSON can be quite large, we might include
    a partial example or a simplified snippet so as not to consume too
    much token space. We ensure the example strictly follows the
    required format to avoid introducing mistakes.
5.  **Incorporating Mock Data:** The prompt may include guidance like
    *\"If the campaign suggests using customer segments or product info
    not provided, create plausible examples. For instance, you can
    assume a \'VIP\' customer tag for VIP segments, or use product names
    like \'Premium Headphones\' as dummy data.\"* This gives the LLM
    license to fabricate reasonable details where needed (since it
    cannot query a database in this context), while keeping the output
    realistic.

The *user message* will then simply contain the actual campaign
description text. By separating system and user messages, we keep the
instructions persistent and clear.

1.  **LLM Generation:** With the above prompt, the LLM will generate a
    response. We expect it to output the flow JSON text. To prevent any
    non-JSON output, we use strategies like:
2.  Explicitly instructing the model that *only JSON is allowed* in the
    answer.
3.  Possibly using special tokens or indicators if the model supports
    function calling or a JSON output mode (for example, some LLM APIs
    allow providing a JSON schema so the model directly produces a JSON
    structure). If available, we would leverage those features to
    constrain the output format.
4.  Using the few-shot example as a format template, which usually
    guides the model to mimic the structure.

The content of the JSON (node logic and messaging) is where the LLM's
intelligence comes in. The model will interpret the campaign description
and decide: - How to structure the flow (e.g. whether to start with a
segment, how many messages, where to put delays or splits). - What each
message should say (using an appropriate tone and including dynamic
fields like `{{first_name}}` or `{{brand_name}}` for personalization). -
What conditions or branch logic to include (based on the intent: for
instance, an abandoned cart scenario will likely include a check for a
recent cart event). - How to utilize discounts or incentives (if the
description implies an offer, the model might include a `discountType`
in a message or purchase node). - Simulated **customer journey**: The
LLM essentially imagines the flow a customer would go through and
encodes that as nodes. For example, for \"boost VIP reorders,\" it might
think: *\"We want VIPs to make another purchase. Possibly identify VIP
customers, send them a special offer message, wait for their response,
and if no response send a reminder.\"* It then translates that into the
appropriate nodes and events.

1.  **Parsing and Correction:** Once the raw JSON text is returned by
    the model, the system will parse it. If the model followed
    instructions correctly, this should parse without error. In case of
    a parse error (which can happen if the model included extra text or
    formatting issues), the system can attempt quick fixes:

2.  Remove any leading/trailing content outside the outer JSON braces.

3.  Ensure proper quoting and escape any illegal characters.

4.  If the JSON is severely malformed or incomplete, it may be necessary
    to re-run the generation. In a re-run, the system might tighten the
    prompt (for example, explicitly saying *\"The previous output was
    invalid JSON because of X. Please output JSON only.\"* or breaking
    the task into smaller steps).

5.  We also have the option to use the model in a *verification mode*:
    e.g. after generation, ask the model (with the output as input) to
    verify if it meets all requirements. However, this adds complexity
    and latency, so the primary approach is to get it right in one go
    through a strong prompt and the validation step.

6.  **Validation & Refinement:** After parsing, the Validation Module
    (described earlier) checks the structure. If any schema violations
    are found, the system can employ a refinement step:

7.  It can either directly adjust the JSON if the fix is straightforward
    (e.g. if an `active` field was false but should be true, or a minor
    field is empty string when it should be omitted or vice versa).

8.  Or, more robustly, feed the issues back to the LLM. For example, the
    system could generate a new prompt: *\"There are errors: Node X is
    missing required field Y. Please fix the JSON.\"* The model can then
    output a corrected JSON. This iterative approach is a form of
    automated review.

9.  We also incorporate the **Important Rules** from the documentation
    as part of validation. For example, rule #1 was to generate unique
    IDs for every node/event, #2 that `initialStepID` must match the
    first real node, #4 that all required fields must have values, etc..
    These are essentially coded into the validation logic and also
    mentioned in the prompt so the model is aware of them upfront.

10. **Final Output:** Once validated, the JSON is returned via the API.
    The expectation is that the output is ready to execute in the SMS
    platform, but as a safety measure, a user might review it (the
    requirement says "compatible with review and downstream execution,"
    meaning a human could double-check it, but they shouldn't need to
    make manual changes for it to work).

Throughout this pipeline, the emphasis is on **automation and
correctness**. The LLM's creative abilities are used to draft the flow
and copy, but the system guides it with strict format rules and
double-checks the result. This combination ensures high-quality outputs:
the flows should both **make marketing sense** (engaging content and
logical sequence) and **conform to the technical schema** needed by the
execution engine.

## API Interface Details

From an integration perspective, using the system involves calling the
API with a campaign description and receiving the JSON flow. Below are
the interface details and how a client would use the API:

-   **Endpoint:** `POST /generateFlow`
-   **Headers:** The request and response use
    `Content-Type: application/json`. If authentication is required (in
    a production setup), for example, a Bearer token or API key header
    would be included, though this is not core to the design task at
    hand.
-   **Request Schema:**
-   `campaignDescription` (string, required): The description of the
    campaign in natural language. This is the key on which the entire
    generation is based.
-   *Future extensions:* We might allow an optional `schemaVersion` (to
    handle future changes in the flow schema), or a flag like `dryRun`
    (where the system validates the description and returns any
    potential issues without generating a full flow). For now, these are
    out of scope.

Example request:

    {
      "campaignDescription": "nurture first-time buyers with abandoned cart recovery and personalized offers"
    }

-   **Response Schema:** On success, HTTP 200 is returned with the JSON
    body representing the flow. There is no additional wrapping; the
    response body is exactly the flow JSON (so that it can be directly
    saved or input to the FlowBuilder system). If needed, we could wrap
    it in an object with metadata, but here simplicity is preferred.

Example response (truncated for illustration):

    {
      "initialStepID": "welcome-msg",
      "steps": [
         {
            "id": "welcome-msg",
            "type": "message",
            "content": "Hi {{first_name}}, thanks for your first purchase! ...",
            "events": [ ... ]
         },
         {
            "id": "check-cart",
            "type": "segment",
            "conditions": [ ... ],
            "events": [ ... ]
         },
         ... 
      ]
    }

In case of an error, the response might be: - **400 Bad Request:** if
the input is missing or invalid (with a JSON error message, e.g.
`{"error": "campaignDescription is required"}`). - **500 Internal Server
Error:** if something went wrong during generation (with a message like
`{"error": "Failed to generate campaign flow"}`). The system logs would
capture details for developers to debug (e.g. the LLM's raw output if it
was not parseable).

-   **API Usage Example:** Suppose a user wants to generate a flow for
    boosting VIP reorders. They would POST
    `{"campaignDescription": "boost VIP reorders"}` to the API. The API
    will respond with a JSON flow (like the one shown in the next
    section). The user (or a tool) can then take that JSON and import it
    into their marketing platform's flow builder. The expectation is
    that minimal to no manual tweaking is needed --- all messages,
    delays, and logic should align with the campaign intent. The user
    can, of course, review the flow and adjust wording or timing if they
    choose, but the heavy lifting of structure and content creation has
    been handled by the AI.

## Example Campaign Flows

To illustrate the system's capabilities, here are two examples: one for
a simple campaign description and one for a more complex campaign. Each
example shows the **input description** and the **generated JSON
output** following the schema.

### Example 1: *"boost VIP reorders"* (Simple Campaign)

**Description:** *Boost VIP reorders* -- The marketer's goal is to
encourage VIP customers to make repeat purchases. The campaign likely
involves identifying VIP customers and sending them a special offer to
reorder, possibly with a discount, and then following up if they don\'t
respond.

**Generated Flow Explanation:** For VIP customers, the flow will first
filter to ensure the recipient is a VIP. Then it sends a personalized
message offering a reward (e.g. 20% off) on their next order. If the
customer responds indicating interest (e.g. replies \"YES\"), the flow
presents a couple of product recommendations to purchase (simulating a
quick reorder process). If the customer does not respond at first or
after seeing products, the flow sends a reminder later. Finally, it ends
the campaign.

**Output JSON:**

    {
      "initialStepID": "vip-segment",
      "steps": [
        {
          "id": "vip-segment",
          "type": "segment",
          "label": "VIP Customer Filter",
          "conditions": [
            {
              "id": 1,
              "type": "property",
              "operator": "has",
              "propertyName": "customer_type",
              "propertyValue": "vip",
              "propertyOperator": "with a value of"
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
              "nextStepID": "vip-message",
              "active": true,
              "parameters": {}
            },
            {
              "id": "vip-no",
              "type": "split",
              "label": "exclude",
              "action": "exclude",
              "nextStepID": "end-node",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "vip-message",
          "type": "message",
          "content": "Hi {{first_name}}! As one of our VIPs, enjoy 20% off your next order. Use code VIP20 at checkout. Reply YES if you'd like some recommendations 👑",
          "text": "Hi {{first_name}}! As one of our VIPs, enjoy 20% off your next order. Use code VIP20 at checkout. Reply YES if you'd like some recommendations 👑",
          "discountType": "percentage",
          "discountValue": "20",
          "discountExpiry": "2025-12-31T23:59:59",
          "handled": false,
          "aiGenerated": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "vip-message-yes",
              "type": "reply",
              "intent": "yes",
              "description": "Customer wants recommendations",
              "nextStepID": "vip-recs",
              "active": true,
              "parameters": {}
            },
            {
              "id": "vip-message-noreply",
              "type": "noreply",
              "after": {
                "value": 1,
                "unit": "days"
              },
              "nextStepID": "vip-reminder",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "vip-recs",
          "type": "product_choice",
          "label": "Product Recommendations",
          "messageType": "standard",
          "messageText": "Sure! Here are a couple of products you might love:\n\n{{Product List}}",
          "text": "Sure! Here are a couple of products you might love:\n\n{{Product List}}",
          "productSelection": "manually",
          "products": [
            {
              "id": "prod-101",
              "label": "Leather Wallet",
              "showLabel": true,
              "uniqueId": 1
            },
            {
              "id": "prod-102",
              "label": "Silk Tie",
              "showLabel": true,
              "uniqueId": 2
            }
          ],
          "productImages": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "vip-recs-buy",
              "type": "reply",
              "intent": "buy",
              "description": "Customer chose a product to buy",
              "nextStepID": "vip-purchase",
              "active": true,
              "parameters": {}
            },
            {
              "id": "vip-recs-noreply",
              "type": "noreply",
              "after": {
                "value": 1,
                "unit": "days"
              },
              "nextStepID": "vip-reminder",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "vip-purchase",
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
              "id": "vip-purchase-end",
              "type": "default",
              "nextStepID": "end-node",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "vip-reminder",
          "type": "message",
          "content": "Just a friendly reminder – your 20% VIP discount (code VIP20) is still available! Let us know if you need any help picking out your next favorite 👍",
          "text": "Just a friendly reminder – your 20% VIP discount (code VIP20) is still available! Let us know if you need any help picking out your next favorite 👍",
          "handled": false,
          "aiGenerated": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "vip-reminder-end",
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

**Discussion:** In this flow: - The **Segment** `vip-segment` checks for
a VIP property. VIP customers go down the \"include\" path; others go to
the End (ensuring non-VIPs do not receive the VIP campaign). - The
**Message** `vip-message` sends a personalized text with a VIP-only
discount code \"VIP20\". It asks the user to reply \"YES\" if they want
recommendations. It also has a no-reply timeout: if the user doesn\'t
respond in 1 day, it triggers the `vip-reminder`. - If the user replies
\"yes\", the **Product Choice** `vip-recs` node sends two sample
products (leather wallet and silk tie) as recommendations (these are
mock products chosen manually for demonstration). The user can respond
(implicitly by choosing one, which we treat as intent \"buy\") to
proceed. If they don\'t respond to the recommendations within a day, the
flow also goes to the same reminder. - The **Purchase** `vip-purchase`
node would handle completing the purchase for whichever product was
chosen (it uses `cartSource: "latest"`, meaning it will take the product
the user selected and process an order). We\'ve set
`sendReminderForNonPurchasers: true` so the system might remind the user
if they abandon the checkout at this final stage (this would be an
automated platform feature outside this flow). - The **Reminder
Message** `vip-reminder` sends a follow-up text reminding the customer
about their discount and offering help. After that, it goes to End.
(Both no-response from the initial message and from the product
recommendation lead here, but the messaging is generic enough to apply
in either case -- basically "you still have your discount, let us know
if you need help".) - Finally, the **End node** cleanly terminates the
flow.

This example shows a relatively straightforward flow: one segment, a
primary message, an optional branch for engagement, and a reminder. It
demonstrates how the LLM can incorporate a VIP condition and create a
logical sequence to boost reorders.

### Example 2: *"nurture first-time buyers with abandoned cart recovery and personalized offers"* (Complex Campaign)

**Description:** *Nurture first-time buyers with abandoned cart recovery
and personalized offers.* -- This campaign is aimed at customers who
have made their first purchase, to encourage them to become repeat
buyers. It specifically calls for handling abandoned carts (if those new
customers add items to the cart but don't complete a purchase) and
providing personalized product offers, likely based on their interests
or past browsing.

**Generated Flow Explanation:** The flow is designed to start after a
customer's first purchase (we assume the marketing team triggers this
nurture flow shortly after someone makes their first order). The LLM
will create a sequence that waits a bit, then checks if the customer has
an abandoned cart. If yes, it initiates a cart recovery sequence
offering to complete the purchase (with a discount incentive). If no
abandoned cart is detected, it instead sends personalized product
recommendations to the customer to entice a new purchase. Both branches
have follow-up messages and eventually converge to an end.

**Output JSON:**

    {
      "initialStepID": "initial-delay",
      "steps": [
        {
          "id": "initial-delay",
          "type": "delay",
          "time": "7",
          "period": "Days",
          "delay": {
            "value": "7",
            "unit": "Days"
          },
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "delay-to-segment",
              "type": "default",
              "nextStepID": "check-cart",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "check-cart",
          "type": "segment",
          "label": "Abandoned Cart Check",
          "conditions": [
            {
              "id": 1,
              "type": "event",
              "operator": "has",
              "action": "started_checkout",
              "filter": "all checkout updates",
              "timePeriod": "within the last 7 Days",
              "timePeriodType": "relative"
            }
          ],
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "cart-yes",
              "type": "split",
              "label": "include",
              "action": "include",
              "nextStepID": "cart-offer",
              "active": true,
              "parameters": {}
            },
            {
              "id": "cart-no",
              "type": "split",
              "label": "exclude",
              "action": "exclude",
              "nextStepID": "personalized-offers",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "cart-offer",
          "type": "purchase_offer",
          "label": "Abandoned Cart Offer",
          "messageType": "standard",
          "messageText": "Hi {{first_name}}, we noticed you left items in your cart:\n\n{{Cart List}}\n\nReply YES to complete your purchase and enjoy 10% off your order!",
          "text": "Hi {{first_name}}, we noticed you left items in your cart:\n\n{{Cart List}}\n\nReply YES to complete your purchase and enjoy 10% off your order!",
          "cartSource": "latest",
          "discount": true,
          "discountType": "percentage",
          "discountPercentage": "10",
          "discountExpiry": false,
          "includeProductImage": true,
          "skipForRecentOrders": false,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "cart-offer-yes",
              "type": "reply",
              "intent": "yes",
              "description": "Customer wants to complete cart purchase",
              "nextStepID": "purchase-step",
              "active": true,
              "parameters": {}
            },
            {
              "id": "cart-offer-noreply",
              "type": "noreply",
              "after": {
                "value": 4,
                "unit": "hours"
              },
              "nextStepID": "cart-reminder",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "cart-reminder",
          "type": "message",
          "content": "Your cart items are still waiting for you! Don’t miss out – complete your purchase to get that 10% off. Need help? We're just a text away.",
          "text": "Your cart items are still waiting for you! Don’t miss out – complete your purchase to get that 10% off. Need help? We're just a text away.",
          "handled": false,
          "aiGenerated": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "cart-reminder-end",
              "type": "default",
              "nextStepID": "end-node",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "personalized-offers",
          "type": "product_choice",
          "label": "Recommended Products",
          "messageType": "standard",
          "messageText": "Hi {{first_name}}, thanks for your first order! We think you'll love these products too:\n\n{{Product List}}",
          "text": "Hi {{first_name}}, thanks for your first order! We think you'll love these products too:\n\n{{Product List}}",
          "productSelection": "popularity",
          "productImages": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "offer-buy",
              "type": "reply",
              "intent": "buy",
              "description": "Customer interested in a recommended product",
              "nextStepID": "purchase-step",
              "active": true,
              "parameters": {}
            },
            {
              "id": "offer-noreply",
              "type": "noreply",
              "after": {
                "value": 2,
                "unit": "days"
              },
              "nextStepID": "offer-reminder",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "offer-reminder",
          "type": "message",
          "content": "Just checking in – those recommendations we sent are still available. Feel free to explore them on our site anytime! We're here if you have any questions.",
          "text": "Just checking in – those recommendations we sent are still available. Feel free to explore them on our site anytime! We're here if you have any questions.",
          "handled": false,
          "aiGenerated": true,
          "active": true,
          "parameters": {},
          "events": [
            {
              "id": "offer-reminder-end",
              "type": "default",
              "nextStepID": "end-node",
              "active": true,
              "parameters": {}
            }
          ]
        },
        {
          "id": "purchase-step",
          "type": "purchase",
          "cartSource": "latest",
          "discount": true,
          "customTotals": false,
          "sendReminderForNonPurchasers": false,
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
          "id": "end-node",
          "type": "end",
          "label": "End",
          "active": true,
          "parameters": {},
          "events": []
        }
      ]
    }

**Discussion:** This flow is more complex and showcases multiple
branches: - It begins with a **Delay** of 7 days (`initial-delay`). This
implies the nurture sequence starts a week after the first purchase,
giving the customer some space. (If the campaign were triggered
immediately after purchase, we might not need a delay, but here it\'s
included to demonstrate scheduling a nurture touchpoint.) - After 7
days, the **Segment** `check-cart` evaluates if the customer has an
abandoned cart scenario. The condition here checks for the event
\"started_checkout\" within the last 7 days. This serves as a proxy for
an abandoned cart (i.e., the user went to checkout but didn't complete
in that time frame). If such an event exists, the customer goes down the
\"include\" branch (`cart-yes`), otherwise the \"exclude\" branch
(`cart-no`). - **Abandoned Cart Branch:** If the user has an abandoned
cart: - The **Purchase Offer** `cart-offer` node sends a message listing
the cart contents (`{{Cart List}}`) and prompts \"Reply YES to complete
your purchase with 10% off\". We set `cartSource: "latest"`, assuming it
will pull the latest cart items for that customer. We also enabled a
discount (10% off) for this purchase (`discountPercentage: 10`). The
content explicitly mentions the 10% off to entice the user. If the user
replies \"yes\", it goes to the `purchase-step` to finalize the order.
If they don\'t reply within 4 hours, a **noreply** event triggers the
`cart-reminder`. - The **Message** `cart-reminder` is a follow-up a few
hours later reminding the user their items are still in the cart and
reiterating the 10% offer. After this reminder message, whether they
respond or not, the flow ends for this branch (the reminder's only event
goes to `end-node`). We chose a relatively short wait (4 hours) for the
reminder since cart recoveries are more effective soon after the
abandonment. - **Personalized Offers Branch:** If the user did *not*
have an abandoned cart (meaning they didn't attempt another purchase
yet): - The **Product Choice** `personalized-offers` node is used to
recommend products. It greets the user thanking them for their first
purchase and then lists some products we think they\'ll love. We used
`productSelection: "popularity"` to simulate pulling in popular items
(in a real system, this might be personalized based on their first
purchase category or browsing data; here we assume popularity as a
proxy). The user can reply by selecting an item (intent \"buy\") which
leads to the common `purchase-step`. If they don't respond in 2 days, a
**noreply** triggers `offer-reminder`. - The **Message**
`offer-reminder` sends 2 days later, gently reminding them about the
recommendations and inviting them to check the site. This is a soft
follow-up to keep the brand in mind without a hard sell. After this, it
goes to `end-node`. - Both branches converge at the **Purchase**
`purchase-step` and the final **End**: - We used a single Purchase node
(`purchase-step`) for either branch's \"buy\" replies. It will handle
whatever context is active (completing either the cart or the chosen
product purchase). We set `discount: true` here as well --- in case the
user came from the cart branch with a discount, this ensures the
discount is applied in the final order. (If they came from the
recommendation branch, no discount code was given, but setting this true
doesn't harm; alternatively, we could have logic to only enable it for
the cart branch. To keep it simple, we left it true globally, assuming
the purchase step can apply any applicable discount if present.) - After
the purchase is processed (or initiated), a default event leads to the
`end-node`. - The **End node** terminates both pathways.

This complex example demonstrates that the LLM can interweave different
features: delays, conditional splits, two different interactive
sequences, and follow-ups, all from a single sentence description. The
flow is fully fleshed out with content: notice the friendly tone and
reassurance in the messages, the use of `{{first_name}}` variable for
personalization, and logically chosen time delays. Such details show the
system's aim to produce not just structurally correct flows, but also
**marketing-sound flows**.

## Conclusion

In summary, the designed system uses an LLM to automatically translate
campaign concepts into actionable SMS flow JSON. The architecture
ensures the output aligns with the provided schema and can be executed
by the platform with minimal tweaks. By combining the creative planning
of an AI with rigorous schema enforcement, marketers can rapidly go from
an idea like \"*boost VIP reorders*\" or \"*welcome new customers*\" to
a ready-to-launch automated campaign. This reduces the manual effort in
campaign setup and allows for quick iteration---users can adjust their
input description and regenerate flows until they get the desired
strategy, which the system will consistently render in correct JSON
format.

This approach not only accelerates campaign deployment but also helps
enforce best practices (through the prompt training and schema rules
baked into the system). As a result, even a short, vague brief can yield
a multi-step, personalized customer journey. The design is extensible:
future improvements might include multi-language support, integration
with real-time data for truly personalized content, and more advanced
prompt strategies (like using the LLM's function calling to fetch
product info). For now, the delivered solution meets the key
requirements and provides a powerful tool for SMS marketing automation.

[\[1\]](https://medium.com/@vi.ha.engr/the-architects-guide-to-llm-system-design-from-prompt-to-production-8be21ebac8bc#:~:text=Every%20call%20to%20an%20LLM,offs%20in%20complexity%20and%20effectiveness)
[\[2\]](https://medium.com/@vi.ha.engr/the-architects-guide-to-llm-system-design-from-prompt-to-production-8be21ebac8bc#:~:text=1)
The Architect's Guide to LLM System Design: From Prompt to Production \|
by Vi Q. Ha \| Medium

<https://medium.com/@vi.ha.engr/the-architects-guide-to-llm-system-design-from-prompt-to-production-8be21ebac8bc>
