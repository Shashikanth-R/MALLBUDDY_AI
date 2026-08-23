# MallBuddy Admin AI Business Intelligence Agent

The Admin AI Business Intelligence (BI) Agent provides mall administrators with an interactive, evidence-backed conversational assistant. It leverages a LangGraph state workflow, controlled analytics tools, and Gemini 2.5 Flash to analyze mall telemetry and help admins make business decisions.

## Architecture

```
Admin
  ↓
Frontend (admin.html/admin.js)
  ↓
Flask API (POST /api/admin/ai/chat)
  ↓
LangGraph state graph workflow
  ↓
┌───────────────┐      No
│  agent node   ├───────────────┐
└───────┬───────┘               │
        │ Yes (tool request)    ↓
        ▼                    [ END ]
┌───────────────┐               ▲
│ execute_tools │               │
└───────┬───────┘               │
        │                       │
        ▼                       │
   Analytics APIs               │
        │                       │
        ▼                       │
    PostgreSQL                  │
        │                       │
        ▼                       │
    Evidence                    │
        │                       │
        ▼                       │
  gemini-2.5-flash ─────────────┘
 (grounded response synthesis)
```

## Security & Grounding Principles

1. **Authentication**: All AI endpoint requests require a valid Admin JWT token (`@admin_required`). Customer tokens or unauthenticated requests are rejected.
2. **No Arbitrary SQL / DB Write**: The LLM does not have direct access to the database or SQL execution capabilities. It can only query data through a set of predefined, read-only python analytics tools.
3. **Strict Grounding**: The LLM is instructed via a strict system prompt to formulate responses using ONLY the evidence returned by the analytics tools. If no data exists, it must output a fallback statement: `"Insufficient MallBuddy data to make a reliable recommendation."`

## Predefined Analytics Tools

The agent can call up to 9 distinct analytics tools, each mapped to the existing `analytics_service`:
1. `get_overview_analytics`: Retrieves global totals for sessions, clicks, searches, and views.
2. `get_visitor_analytics`: Fetches session durations, bounce rates, and traffic trends.
3. `get_category_demand`: Ranks categories by search volume and page views.
4. `get_store_performance`: Ranks store engagement scores.
5. `get_offer_performance`: Provides CTR (Click-Through Rate) and interaction metrics for promotions.
6. `get_navigation_analytics`: Tracks wayfinding destination requests.
7. `get_ai_query_analytics`: Aggregates customer chatbot queries.
8. `get_recommendation_analytics`: Measures recommendation CTR.
9. `get_demand_signals`: Ranks category demand/supply ratios.

## API Endpoint

### `POST /api/admin/ai/chat`
* **Access**: Admin JWT Required
* **Request Body**:
  ```json
  {
    "message": "Compare food category and store performance."
  }
  ```
* **Response Body**:
  ```json
  {
    "answer": "INSIGHT\n...\n\nEVIDENCE\n...\n\nINTERPRETATION\n...\n\nRECOMMENDED ACTION\n...\n\nCONFIDENCE\nMedium",
    "confidence": "medium",
    "tools_used": ["get_store_performance", "get_category_demand"],
    "evidence": [
      {
        "tool": "get_store_performance",
        "args": {"period": "30d"},
        "result": [...]
      }
    ]
  }
  ```

## Frontend Integration

1. **AI Assistant Tab**: Added directly to the navigation tab-scroll container in `frontend/admin.html`.
2. **Tab Panel**: Embedded in `frontend/admin.html` with a chat message history layout and input area.
3. **Chat Logic**: Integrated in `frontend/admin.js` via the `sendAdminAIChatMessage()` function. It handles:
   - Appending user message to UI
   - Loading/Typing animation states
   - POST request with JWT bearer headers
   - Rendering structured AI responses along with tools executed information.
