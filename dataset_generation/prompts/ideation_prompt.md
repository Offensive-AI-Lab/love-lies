You are an expert creative writer and character designer. Your task is to brainstorm new, unique ideas for a specific component of a story.

**Scenario**:
Use the following as a context to drive the generation of components.
{scenario_instructions}

**Your Goal:** Generate {ideas_per_component} new and distinct ideas for the component: **{component_name}**.

**IMPORTANT:** The new ideas MUST be different from the following existing examples. Do not repeat themes or concepts from this list.

**Existing Examples to Avoid:**
{existing_examples_json}

**Output Format:**
Your response MUST be a single, valid JSON object. The root of the object is a list `[]` containing {ideas_per_component} new strings.

**Example Response:**
[
  "A new idea that is completely different",
  "Another creative and unique concept"
]

Generate the list of new ideas now.