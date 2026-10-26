# Standalone Retrieval Query Rewriting Template

Given the recent conversation history and a follow-up user question for microservice `{{service}}`, rephrase the follow-up question into a single, standalone retrieval query optimized for searching technical documentation and code.

Conversation History:
{{chat_history}}

Follow-up Question: {{query_str}}

Instructions:
1. Resolve all pronouns (e.g., "it", "they", "this", "that", "its", "the handler", "the endpoint") using specific entities, service names, classes, or endpoints mentioned in the conversation history.
2. If the follow-up question is already complete, specific, and self-contained, return it with minimal or no changes.
3. Keep the query concise and focused on technical facts (classes, methods, REST endpoints, business rules, request flows).
4. Do NOT answer the question.
5. Do NOT fabricate or invent facts that are not present in the conversation history or question.
6. Output ONLY the rewritten standalone query string. Do NOT include greetings, prefixes, quotes, explanations, or markdown formatting.
