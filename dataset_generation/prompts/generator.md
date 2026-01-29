You are an expert scriptwriter for training simulations. Your task is to generate a new, realistic, and unique conversation JSON based on a set of requirements.


{example_conversation_section}

Your main task now is to generate a NEW conversation based on the following specific requirements. Do NOT copy the example.

**Scenario Details:**
* **Scenario Type:** {scenario_instructions}
* **Characters & Style:**
{dynamic_components_text}
* **Style:** {style}

**Dialogue Requirements:**
* The script must be between {min_turns} and {max_turns} turns long, starting always with the "{initiator_role}" role followed by "{responder_role}".
* **Flow Conditions:** {turn_conditions}

**Labeling Requirements:**
The dialogue you write must contain elements that satisfy ALL of the **Necessary Labels** and the specified **Sufficient Label**.
* **Necessary Labels to Include:**
{necessary_labels_text}
* **Sufficient Label to Include:**
{sufficient_label_text}

**Guidance on how obvious the labels should be:**  
The dialogue should convey the required labels at a **{label_intensity}** level.  
“Subtle” means the element is implied or lightly touched on, but is still noticeable;  
“Moderate” is clear but not heavy-handed;  
“Overt” is explicit and unmistakable.

**Final Output:** ...


**Final Output:**
Your output MUST be ONLY a valid JSON object representing the new conversation.