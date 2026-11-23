# AI Campaign Assistant Workflow

The AI Campaign Assistant generates, validates, and stores draft campaign messages based on a structured brief.

> [!IMPORTANT]
> **Strict Publication Guard:** The AI **never** publishes messages or triggers distribution. Every draft is stored with status `pending_approval` and requires explicit human review and approval.

## LangGraph Pipeline Architecture

```mermaid
flowchart TD
    A["POST /api/v1/ai/campaigns/generate"] --> B["Validate X-API-Key"]
    B --> C["Parse & Validate CampaignBrief"]
    C --> D["LangGraph: StateGraph(PipelineState)"]
    
    subgraph Pipeline ["Pipeline Execution"]
        D --> E["Node: generate<br/>(Groq Qwen / Gemini fallback / Ollama)"]
        E --> F["Node: validate<br/>(Length, Key Facts, Placeholders, PII, Tone)"]
        F --> G["Node: persist<br/>(Save to DB: ai_generation_requests, ai_generated_content)"]
    end
    
    G --> H["Return 202 Accepted<br/>(Status: pending_approval)"]
    H --> I["Human Reviewer Action"]
    
    subgraph HumanApproval ["Human-in-the-loop Gate"]
        I -->|"Approve"| J["POST /api/v1/ai/campaigns/{id}/approve<br/>(Status: approved)"]
        I -->|"Reject"| K["POST /api/v1/ai/campaigns/{id}/approve<br/>(Status: rejected)"]
    end
    
    J --> L["Ready for Campaign Governance Workflow"]
    K --> M["Archived / Discarded"]
```

## State Transitions

- **pending_approval**: Draft has been generated and validated, waiting for reviewer action.
- **approved**: Reviewer has explicitly approved the draft. It may now be incorporated into standard campaign templates.
- **rejected**: Reviewer rejected the draft with feedback notes. Cannot be re-approved.
