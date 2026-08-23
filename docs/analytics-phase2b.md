# MallBuddy Analytics Engine (Phase 2B) Documentation

This document describes the design, business calculations, API reference, and security model for the Phase 2B MallBuddy Real Analytics Engine and Admin API.

---

## 1. Architectural Overview

The MallBuddy Analytics Engine turns raw user interactions (telemetry) collected in Phase 2A into actionable business-intelligence insights displayed on the MallBuddy Admin Dashboard.

```
REAL USER ACTION
       ↓
telemetry/user_events
       ↓
Analytics calculations (analytics_service.py)
       ↓
Admin Analytics APIs (admin_routes.py)
       ↓
Admin Dashboard (admin.js)
```

---

## 2. Business Definitions & Formulas

### 2.1. Sessions & Retention
- **Total Sessions**: Count of all sessions initiated within the period.
- **Unique Visitors**: Count of unique visitors identified by the formula: `coalesce(user_id, session_token)`.
- **New Sessions**: Number of sessions belonging to visitors whose very first session started within the specified period.
- **Returning Visitors**: Calculated as: `max(0, unique_visitors - new_sessions)`.
- **Average Session Duration**: Total session duration (seconds) divided by the number of ended sessions:
  $$\text{Avg Duration} = \frac{\sum (\text{ended\_at} - \text{started\_at})}{\text{count of sessions where ended\_at is not null}}$$

### 2.2. Engagement Score
To rank stores and gauge active user interest, an **Engagement Score** is computed for each store using a weighted formula based on user actions:
$$\text{Engagement Score} = (1.0 \times \text{views}) + (1.2 \times \text{searches}) + (2.0 \times \text{nav\_requests}) + (1.5 \times \text{offer\_interactions}) + (1.5 \times \text{recommendation\_interactions})$$
*Weights reflect the depth of intent, where actual navigation (intent to visit physically) has the highest weight.*

### 2.3. Click-Through Rate (CTR)
For offers and recommendation slots, CTR is calculated as:
$$\text{CTR (\%)} = \left( \frac{\text{clicks}}{\text{views}} \right) \times 100$$
*(If views is 0, the CTR defaults to 0.0%)*

### 2.4. Demand Signal Levels
Determines retail interest for categories based on a combination of search queries, navigation actions, and store density:
$$\text{Supply Gap Ratio} = \frac{\text{searches + navigation}}{\text{active\_store\_count}}$$
Based on the supply-gap ratio, categories are classified into:
- **Critical Gap** (High demand, low supply)
- **High Demand**
- **Moderate**
- **Balanced**

---

## 3. Telemetry Event & Model Mapping

Telemetry events recorded in Phase 2A map to the business calculations as follows:

| Business Metric | Event Type | Target Columns / Metadata |
| :--- | :--- | :--- |
| **Store Views** | `store_view` | `store_id` |
| **Store Searches** | `store_search` | `category_id`, `search_query` |
| **Navigation Requests**| `navigation_request` | `store_id` |
| **Offer Views** | `offer_view` | `offer_id` |
| **Offer Clicks** | `offer_click` | `offer_id` |
| **AI Queries** | `ai_query` | `search_query` |
| **Recommendation Views**| `recommendation_view` | `metadata_` JSON containing `$.type` |
| **Recommendation Clicks**| `recommendation_click`| `metadata_` JSON containing `$.type` |

*Note: All analytics queries exclude synthetic data (`is_synthetic == True`) by default to prevent testing noise from polluting business dashboards.*

---

## 4. API Endpoint Reference

All endpoints base URL: `/api/admin`

### 4.1. Global Parameters (Query Parameters)
- `period` (optional): Options are `today`, `7d`, `30d` (default).
- `start_date` (optional): ISO format string (e.g. `2026-08-23T00:00:00`). If specified, `end_date` must also be specified.
- `end_date` (optional): ISO format string.

### 4.2. Overview Analytics
- **Path**: `GET /analytics/overview`
- **Response sample**:
  ```json
  {
    "total_sessions": 120,
    "unique_visitors": 80,
    "total_events": 450,
    "store_views": 180,
    "store_searches": 90,
    "navigation_requests": 65,
    "offer_clicks": 45,
    "ai_queries": 70
  }
  ```

### 4.3. Visitor Analytics
- **Path**: `GET /analytics/visitors`
- **Response sample**:
  ```json
  {
    "unique_visitors": 80,
    "new_sessions": 50,
    "returning_visitors": 30,
    "avg_session_seconds": 184.5,
    "daily_trend": [
      { "date": "2026-08-22", "unique_visitors": 12, "sessions": 15 }
    ],
    "hourly_trend": [
      { "hour": 14, "sessions": 8 }
    ]
  }
  ```

### 4.4. Category Performance
- **Path**: `GET /analytics/categories`
- **Response sample**:
  ```json
  [
    {
      "category": "Fashion",
      "views": 120,
      "searches": 45,
      "navigation_requests": 20
    }
  ]
  ```

### 4.5. Store Performance
- **Path**: `GET /analytics/stores`
- **Response sample**:
  ```json
  [
    {
      "store_id": 3,
      "store_name": "Zara",
      "category": "Fashion",
      "store_views": 85,
      "searches": 22,
      "navigation_requests": 15,
      "offer_interactions": 30,
      "recommendation_interactions": 10,
      "unique_visitors": 45,
      "engagement_score": 182.4
    }
  ]
  ```

### 4.6. Offer CTR Performance
- **Path**: `GET /analytics/offers`
- **Response sample**:
  ```json
  [
    {
      "offer_id": 1,
      "title": "Summer Sale 20%",
      "store_name": "H&M",
      "views": 200,
      "clicks": 40,
      "unique_visitors": 150,
      "ctr": 20.0
    }
  ]
  ```

### 4.7. Wayfinding & Navigation Performance
- **Path**: `GET /analytics/navigation`
- **Response sample**:
  ```json
  {
    "total_navigation_requests": 65,
    "popular_destinations": [
      {
        "store_id": 3,
        "store_name": "Zara",
        "category": "Fashion",
        "navigation_requests": 15
      }
    ]
  }
  ```

### 4.8. AI Query Trends
- **Path**: `GET /analytics/ai-queries`
- **Response sample**:
  ```json
  {
    "total_ai_queries": 70,
    "unique_visitors": 45,
    "popular_questions": [
      { "query": "where is the restrooms", "count": 12 }
    ],
    "query_volume_by_day": [
      { "date": "2026-08-22", "count": 25 }
    ],
    "query_volume_by_hour": [
      { "hour": 15, "count": 9 }
    ]
  }
  ```

### 4.9. Personalization Slots
- **Path**: `GET /analytics/recommendations`
- **Response sample**:
  ```json
  {
    "total_views": 350,
    "total_clicks": 70,
    "ctr": 20.0,
    "performance_by_type": [
      {
        "recommendation_type": "fashion",
        "views": 150,
        "clicks": 35,
        "ctr": 23.33
      }
    ]
  }
  ```

### 4.10. Retail Demand Signals
- **Path**: `GET /analytics/demand`
- **Response sample**:
  ```json
  [
    {
      "category": "Food & Beverages",
      "searches_and_navigation": 85,
      "active_stores": 2,
      "supply_gap_ratio": 42.5,
      "signal": "Critical Gap"
    }
  ]
  ```

---

## 5. Security & Authorization Model

### 5.1. Token Generation
During login, admin tokens are generated via `/api/auth/admin/login`. These tokens are signed using the JWT secret and include custom claims:
```json
{
  "role": "admin",
  "is_admin": true
}
```

### 5.2. Server-Side Verification
The `@admin_required` custom decorator intercepts all incoming dashboard and analytics requests to guarantee secure execution:
1. **JWT Verification**: Checks that a valid Bearer token is provided in the headers.
2. **Claim Validation**: Extracts claims from the JWT and rejects the request with a `403 Forbidden` status code if `"role"` is not `"admin"` or `"is_admin"` is not `true`.
3. **Database Account Verification**: Performs a quick query to confirm the admin user exists in the `admins` table and is marked `is_active == True`.
