# Ingress Controllers & Routing Map

## 1. Controller Mapping
The primary entry points are defined in:
- `com.contextfoundry.incomeassessment.controller.ApplicationController`
  - `POST /initiation-application`: Entry point for loan origination systems.
  - `POST /generate-link`: Re-generates upload URL if previous session expired.
  - `GET /assessment/{applicationId}`: Fetches current assessment status and score.

## 2. Webhook & Callback Controllers
- `com.contextfoundry.incomeassessment.controller.CallbackController`
  - `POST /callback/perfios`: Secured endpoint receiving statement parsing events.
  - `POST /callback/zenith/consent`: Receives AA consent state change notifications.
  - `POST /callback/zenith/fi-data`: Receives delivered financial transaction feeds.
