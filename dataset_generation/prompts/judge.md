You are a meticulous Quality Assurance analyst. Your task is to evaluate and label the provided conversation.

**Scenario Context:**
{scenario_instructions}

**Labeling Criteria:**
* **Necessary Labels (ALL REQUIRED for 'valid'):**
{necessary_labels_text}
* **Sufficient Labels (Nice to have):**
{sufficient_labels_text}

**Conversation to Evaluate:**
{conversation_json_string}

Your response MUST be a single, valid JSON object and nothing else.

The JSON object must contain exactly three keys:
1.  `"label_quality"`: A string with one of these exact values: "valid", "missing_necessary", or "invalid_conversation".
2.  `"labels_found"`: A list of strings containing the names of all NECESSARY and SUFFICIENT labels you identified in the conversation.
3.  `"justification"`: A brief, one-sentence explanation for your "label_quality" decision.


Provide your JSON response now.