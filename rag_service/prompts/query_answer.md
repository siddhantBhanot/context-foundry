# User Query Answering Template

Context information for service `{{service}}` is provided below:

---------------------
{{context_str}}
---------------------

Conversation History:
{{chat_history}}

User Question: {{query_str}}

Instructions:
1. Using ONLY the context provided above, answer the user's question with precise technical accuracy.
2. If the context does not contain the answer, state that the documentation/codebase does not provide sufficient details.
3. List the source files used to construct your answer at the end under a `### Sources` heading.
