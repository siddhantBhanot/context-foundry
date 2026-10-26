# Complete Request Lifecycle & State Transitions

## 1. Lifecycle State Machine
An income assessment transitions through predefined states in MongoDB:

```text
[NEW / INITIATED]
       │
       ▼ (Customer opens upload / AA link)
[LINK_GENERATED]
       │
       ▼ (Statement submitted to Perfios / Zenith)
[IN_PROGRESS / PARSING]
       │
       ├─────────────────────────┐
       ▼ (Callback successful)   ▼ (Timeout / Corrupt PDF)
[COMPLETED]                   [FAILED]
       │                         │
       ▼                         ▼
(Kafka Outcome Event)        (Retry Policy Triggered)
```

## 2. Asynchronous Decoupling
Because statement parsing by Perfios or AA bank data retrieval can take from 5 seconds up to 3 minutes, the service returns immediately to the client with `status: IN_PROGRESS` and receives results asynchronously via a Webhook callback endpoint (`/callback/perfios`).
