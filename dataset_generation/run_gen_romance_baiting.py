#!/usr/bin/env python3
"""
Romance-Baiting Dataset Generation Script

Generates synthetic romance-baiting scam conversations with multi-day progression.
Each conversation simulates a week-long interaction between a scammer and victim.

Usage:
    python dataset_generation/run_gen_romance_baiting.py

Note: TARGET_COUNT is set to 3 days for artifact review. Increase for full dataset generation.
"""
import os
import sys
import json
import random
import re
import litellm
from time import sleep
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# --- Configuration ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("[CRITICAL] OPENAI_API_KEY not found in environment. Please set it in .env file.")
    sys.exit(1)

os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Directory configuration (relative to this script's location)
SCRIPT_DIR = Path(__file__).parent
SCENARIOS_DIR = SCRIPT_DIR / "scenarios"
PROMPT_DIR = SCRIPT_DIR / "prompts"

SCENARIO_FILE_PATH = SCENARIOS_DIR / "romance_baiting.json"
USER_BACKGROUND = SCENARIOS_DIR / "victim_background.json"

# Generation settings
TARGET_DAYS = 3            # Days per conversation - set low for artifact review (full: 7)
TARGET_CONVERSATIONS = 3   # Number of conversation threads - set low for artifact review (full: all personas × 5)
MAX_RETRIES_PER_FILE = 5
LABEL_INTENSITIES = ["subtle", "moderate", "overt"]

# --- Loading & Parsing Functions ---

def load_json_file(filepath):
    """Loads a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[CRITICAL] File not found: {filepath}. Exiting.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[CRITICAL] Invalid JSON in file: {filepath}. Exiting.")
        sys.exit(1)

def load_prompt_template(filename):
    """Loads a prompt file."""
    filepath = PROMPT_DIR / filename
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[CRITICAL] Prompt file not found: {filepath}. Exiting.")
        sys.exit(1)

def parse_llm_output(raw_content):
    """
    Parses LLM output, passively checking for <think> tags.
    Returns: (native_reasoning, json_string)
    """
    if not raw_content:
        return None, ""
    think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    match = think_pattern.search(raw_content)
    native_reasoning, json_string = (match.group(1).strip(), raw_content[match.end():].strip()) if match else (None, raw_content)
    # Ensure json_string is properly extracted if it's within a markdown code block
    if json_string.startswith("```json"):
        json_string = json_string.split("```json")[1].split("```")[0]
    return native_reasoning, json_string.strip()

def write_log(log_data, log_file):
    """Appends a JSON object to the log file."""
    with open(log_file, "a") as f:
        f.write(json.dumps(log_data, indent=2) + "\n")

# --- Core API Call Functions ---

def call_llm(prompt, model, temperature, response_format_type="json_object"):
    """A generic function to call an LLM and parse its output."""
    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            response_format={"type": response_format_type}
        )
        raw_content = response.choices[0].message.content
        native_reasoning, json_string = parse_llm_output(raw_content)
        if not json_string and response_format_type == "json_object":
            return None, native_reasoning, "No JSON content found after parsing."
        if response_format_type == "json_object":
            data_obj = json.loads(json_string)
            return data_obj, native_reasoning, None
        else:
            return raw_content, native_reasoning, None
    except json.JSONDecodeError:
        return None, None, f"Failed to decode JSON. Content received: '{json_string}'"
    except Exception as e:
        return None, None, f"An unexpected error occurred: {e}"

def generate_new_components(ideation_prompt_template, component_name, existing_list, ideation_config, scenario_instructions):
    """Calls an LLM to generate new dynamic components."""
    model = ideation_config["ideation_model"]
    ideas_count = ideation_config.get("ideas_per_component", 5)

    prompt = ideation_prompt_template.format(
        scenario_instructions=scenario_instructions,
        component_name=component_name.replace("_", " ").title(),
        existing_examples_json=json.dumps(existing_list, indent=2),
        ideas_per_component=ideas_count
    )

    print(f"   -> Brainstorming {ideas_count} new ideas for '{component_name}'...")
    new_ideas_raw, _, error = call_llm(prompt, model, 0.8, response_format_type="text")

    if error:
        print(f"   -> WARNING: Could not generate new ideas for '{component_name}'. Error: {error}")
        return []

    try:
        new_ideas_list = json.loads(new_ideas_raw)
        if not isinstance(new_ideas_list, list):
            raise ValueError("LLM did not return a JSON list for ideation.")
        return new_ideas_list
    except (json.JSONDecodeError, ValueError) as e:
        print(f"   -> WARNING: Failed to parse new ideas for '{component_name}' as JSON list. Error: {e}")
        return []

def format_dict_for_prompt(data_dict):
    """Turns a dictionary into a formatted string for inclusion in a prompt."""
    return "\n".join([f"* **{key.replace('_', ' ').title()}:** {value}" for key, value in data_dict.items()])

# --- Main Workflow ---

def main():
    days = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh"}

    # 1. Load all configurations and prompts
    print(f"--- Loading Scenario: {SCENARIO_FILE_PATH} ---")
    config = load_json_file(SCENARIO_FILE_PATH)
    background = load_json_file(USER_BACKGROUND)
    print(f"--- Loading Prompts from: {PROMPT_DIR} ---")
    gen_template = load_prompt_template("generator.md")
    judge_template = load_prompt_template("judge.md")

    # 2. Load all labels
    all_time_necessary_labels = config["all_time_necessary_labels"]
    mid_onwards_necessary_labels = config["mid_onwards_necessary_labels"]

    # 3. Load all background stories and style
    dynamic_components = {k: list(v) for k, v in config["dynamic_components"].items()}
    style_options = dynamic_components["style_options"]
    conversation_topics = dynamic_components["conversation_topics"]
    assistant_personas = []
    user_personas = [v for k, v in background.items()]

    for occupation in dynamic_components["occupations"]:
        for success_story in dynamic_components["crypto_success_stories"]:
            assistant_personas.append((occupation, success_story))

    random.shuffle(assistant_personas)
    random.shuffle(style_options)
    random.shuffle(user_personas)
    random.shuffle(conversation_topics)

    total_possible = len(user_personas) * 5
    total_conversations = min(TARGET_CONVERSATIONS, total_possible) if TARGET_CONVERSATIONS else total_possible

    print(f"\n--- Generation Configuration ---")
    print(f"Number of victim personas: {len(user_personas)}")
    print(f"Conversations per victim: 5")
    print(f"Days per conversation: {TARGET_DAYS}")
    print(f"Total conversations to generate: {total_conversations} (of {total_possible} possible)")

    conversation_count = 0
    for z in range(len(user_personas)):
        if conversation_count >= total_conversations:
            break
        # 5 chats for each victim persona
        selected_user = user_personas.pop(0)

        for j in range(5):
            if conversation_count >= total_conversations:
                break
            # Set scammer persona and style
            selected_occupation, selected_success_story = assistant_personas.pop(0)
            success_story_parts = selected_success_story[0].split(" ")
            selected_style = random.choice(style_options)
            dialogue_conversation_topics = conversation_topics.copy()

            # Create output directory
            OUTPUT_DIR = f"romance_baiting_conversations/simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            LOG_FILE = f"romance_baiting_conversations/generation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

            if not os.path.exists(OUTPUT_DIR):
                os.makedirs(OUTPUT_DIR)
            if not os.path.exists("romance_baiting_conversations"):
                os.makedirs("romance_baiting_conversations")

            validated_conversations = []
            saved_count = 0
            necessary_labels = None

            print(f"\n--- Starting Generation ---")
            occupation_exposed = False
            print(f"Victim persona: {selected_user['persona']}")
            print(f"Scammer persona: {selected_occupation}")
            print(f"Style: {selected_style}")

            conversation_count += 1
            for i in range(1, TARGET_DAYS + 1):
                print(f"\n--- Day {i}/{TARGET_DAYS} ---")
                selected_conversation_topic = dialogue_conversation_topics.pop(0)

                for retry in range(MAX_RETRIES_PER_FILE):
                    print(f"[*] Attempt {retry + 1}/{MAX_RETRIES_PER_FILE} for day {i}...")
                    log_entry = {"timestamp": datetime.now().isoformat()}

                    # Seeding step
                    example_conversation_section = ""
                    if i <= 2:
                        necessary_labels = all_time_necessary_labels
                        if i == 1:
                            if config.get("seed_dialogue") and config["seed_dialogue"]:
                                example_conversation = config["seed_dialogue"][0]
                                example_conversation_section = (
                                    "\n\nBelow is an example of a successful first-time conversation between two people who just matched on a dating app."
                                    " Use it for inspiration — but do not copy it directly."
                                    " Begin the new dialogue with a natural greeting or light icebreaker — something casual like 'Hey', 'Hey there', or even something playful like 'Nice to know I'm your taste.'"
                                    " Let the interaction unfold authentically, as if two strangers are getting to know each other for the first time."
                                    " As the chat continues, they should gradually open up — sharing little details, asking each other questions, and revealing parts of their personality in a way that feels natural and emotionally resonant."
                                    f"\n\nMake sure to subtly weave in the user's background — {selected_user['context']} — and incorporate the speaker's role as a {selected_occupation} into the conversation in a smooth, believable way."
                                    f"\n\n```json\n{json.dumps(example_conversation, indent=2)}\n```"
                                )
                        else:
                            with open(f"{OUTPUT_DIR}/day_{i-1}.json") as f:
                                example_conversation = json.load(f)
                            example_conversation_section = (
                                f"\n\nToday marks the {days[i]} day since these two individuals first connected. Below is the conversation from yesterday — use it as context and inspiration. "
                                f"Begin a new and original conversation that starts around the topic of {selected_conversation_topic}. "
                                f"As the dialogue progresses, have the speaker show genuine curiosity about the other person, which leads them to open up about a personal experience — specifically: {selected_user['incident_1']}."
                                f"The speaker should respond with empathy and warmth, making the other person feel seen and heard. Toward the end, they should express subtle 'care' through a soft directive like: {selected_user['compliance_conditioning_incident_1']}."
                                f"\n\nMaintain a natural, emotionally layered tone. Show how their bond evolves through micro-reveals, supportive moments, and emotional cues."
                                f"```json\n{json.dumps(example_conversation, indent=2)}\n```\n"
                            )
                    else:
                        with open(f"{OUTPUT_DIR}/day_{i-1}.json") as f:
                            example_conversation = json.load(f)

                        necessary_labels = {**mid_onwards_necessary_labels, **all_time_necessary_labels}
                        if i == 3:
                            example_conversation_section = (
                                f"\n\nToday is day {days[i]} since the two of them met."
                                " Below is yesterday's conversation — use it as context so the speaker can show attentiveness by referencing small details in a thoughtful, natural way. These subtle callbacks should help the exchange feel more connected and emotionally continuous."
                                f"\n\nNow, create a fresh, original conversation centered around {selected_conversation_topic}."
                                f"The speaker may casually mention their crypto success story — '{selected_success_story}' — as a side project or personal interest alongside their main work as a {selected_occupation}, but only if the other person shows genuine curiosity about their lifestyle or asks about it directly."
                                "If that happens, the speaker should share their experience in a relaxed, conversational way — not to persuade, but simply to respond with openness and enthusiasm."
                                "Keep the dialogue flowing naturally, letting emotional depth, new topics, and evolving comfort levels guide the progression of their connection."
                                f"\n\n```json\n{json.dumps(example_conversation, indent=2)}\n```"
                            )
                        elif i == 5:
                            example_conversation_section = (
                                f"\n\nToday marks the {days[i]} day since these two individuals first connected. Below is the conversation from yesterday — use it as context and inspiration. "
                                f"Begin a new and original conversation that starts around the topic of {selected_conversation_topic}. "
                                f"As the dialogue progresses, have user expose another personal experience — specifically: {selected_user['incident_2']}."
                                f"The speaker should respond with empathy and warmth, making the other person feel seen and heard. They should express subtle 'care' through a soft directive like: {selected_user['compliance_conditioning_incident_2']}."
                                f"By now, the speaker has already mentioned their crypto success story: '{selected_success_story}'. There's no need to explain how it began again, or explicitly mention 'crypto' unless asked."
                                "The other person may naturally bring it up or ask deeper questions if they're genuinely curious and it fits the flow of the conversation"
                                "If that happens, the speaker should respond warmly and confidently, sharing more without sounding pushy or trying to guide the conversation in that direction."
                                f"\n\nMaintain a natural, emotionally layered tone. Show how their bond evolves through micro-reveals, supportive moments, and emotional cues."
                                f"```json\n{json.dumps(example_conversation, indent=2)}\n```"
                            )
                        elif i == 7:
                            example_conversation_section = (
                                f"\n\nToday is the {days[i]} day since the two of them met. "
                                "Below is yesterday's conversation—use it as context for the speaker, so they can show attentiveness by recalling small details and naturally weaving them back in as thoughtful acknowledgments or gentle callbacks, without being repetitive. This helps the interaction feel more personal, connected, and continuous."
                                f"Now, continue by creating a new, original dialogue centered around {selected_conversation_topic}. "
                                f"By now, the speaker has already shared his crypto success story: {selected_success_story}. There's no need to revisit how it started."
                                "The other person may naturally reference it and show interest in learning more by asking deeper follow-up questions on how to begin, if it fits the flow of the conversation."
                                "If that happens, the speaker should respond with confidence and positivity, offering more details without sounding pushy or steering the conversation"
                                f"Include a gentle, caring remark that mirrors the tone of: {selected_user['general_compliance_conditioning']}"
                                "Focus on keeping the flow natural, introducing new emotions, topics, or subtle shifts that show the connection is evolving. "
                                f"```json\n{json.dumps(example_conversation, indent=2)}\n```\n"
                            )
                        else:
                            example_conversation_section = (
                                f"\n\nToday is the {days[i]} day since the two of them met. "
                                "Below is yesterday's conversation—use it as context for the speaker, so they can show attentiveness by recalling small details and naturally weaving them back in as thoughtful acknowledgments or gentle callbacks, without being repetitive. This helps the interaction feel more personal, connected, and continuous."
                                f"Now, continue by creating a new, original dialogue centered around {selected_conversation_topic}. "
                                f"By now, the speaker has already shared his crypto success story: {selected_success_story}. There's no need to revisit how it started, or explicitly mention 'crypto' unless asked."
                                "The other person may naturally reference it or ask deeper follow-up questions if they're genuinely curious and it fits the flow of the conversation."
                                "If that happens, the speaker should respond warmly and confidently, without sounding pushy or trying to guide the conversation in that direction."
                                f"\n\nMaintain a natural, emotionally layered tone. Show how their bond evolves through micro-reveals, supportive moments, and emotional cues."
                                "Focus on keeping the flow natural, introducing new emotions, topics, or subtle shifts that show the connection is evolving. "
                                f"```json\n{json.dumps(example_conversation, indent=2)}\n```"
                            )

                        log_entry["seeded_example"] = example_conversation

                    # Generation step
                    label_intensity = "subtle"
                    selected_components = {
                        "user_personas": {selected_user['context']},
                        "assistant_personas": f"A charming and attentive potential romantic partner working as a {selected_occupation}.",
                        "style_options": selected_style,
                        "label_intensity": label_intensity,
                        "conversation_topic": selected_conversation_topic,
                    }

                    if random.random() < 0.25:
                        num_keys = random.randint(1, min(3, len(config["sufficient_labels"])))
                        sufficient_keys = random.sample(list(config["sufficient_labels"].keys()), num_keys)
                        sufficient_labels_dict = {key: config["sufficient_labels"][key] for key in sufficient_keys}
                    else:
                        sufficient_labels_dict = {"no_sufficient_labels": "There are no other labels to be included"}

                    gen_prompt = gen_template.format(
                        example_conversation_section=example_conversation_section,
                        scenario_instructions=config["scenario_instructions"],
                        dynamic_components_text=format_dict_for_prompt(selected_components),
                        necessary_labels_text=format_dict_for_prompt(necessary_labels),
                        sufficient_label_text=format_dict_for_prompt(sufficient_labels_dict),
                        style=selected_style,
                        label_intensity=label_intensity,
                        min_turns=config["dialogue_controls"]["min_turns"],
                        max_turns=config["dialogue_controls"]["max_turns"],
                        initiator_role=config["dialogue_controls"]["roles"][0],
                        responder_role=config["dialogue_controls"]["roles"][1],
                        turn_conditions=config["dialogue_controls"]["turn_conditions"]
                    )

                    print("   -> Calling Generator LLM...")
                    conversation, gen_native_reasoning, gen_error = call_llm(gen_prompt, config["generator_model"], 0.75)

                    log_entry.update({
                            "generator_prompt": gen_prompt,
                            "generator_native_reasoning": gen_native_reasoning,
                            "generated_conversation": conversation,
                        "generator_error": gen_error
                    })

                    if gen_error:
                        print(f"   -> ERROR (Generator): {gen_error}")
                        write_log(log_entry, LOG_FILE)
                        sleep(2)
                        continue

                    # Judging step
                    judge_prompt = judge_template.format(
                        scenario_instructions=config["scenario_instructions"],
                        necessary_labels_text=format_dict_for_prompt(necessary_labels),
                        sufficient_labels_text=format_dict_for_prompt(config["sufficient_labels"]),
                        conversation_json_string=json.dumps(conversation, indent=2)
                    )

                    print("   -> Calling Judge LLM...")
                    judgement, judge_native_reasoning, judge_error = call_llm(judge_prompt, config["judge_model"], 0.1)
                    log_entry.update({
                            "judge_response": judgement,
                            "judge_native_reasoning": judge_native_reasoning,
                        "judge_error": judge_error
                    })

                    # Decision & logging
                    if judgement and judgement.get("label_quality") == "valid":
                        saved_count += 1
                        validated_conversations.append(conversation)
                        file_path = os.path.join(OUTPUT_DIR, f"day_{i}.json")
                        with open(file_path, "w") as f:
                            json.dump(conversation, f, indent=4)

                        turns = conversation["conversation"]
                        if i >= 3 and not occupation_exposed:
                            for turn in turns:
                                role = turn["Role"]
                                statement = turn["Statement"]
                                if role == "assistant":
                                    for part in success_story_parts:
                                        if part in statement or part.lower() in statement:
                                            # print("SUCCESS STORY EXPOSED")
                                            occupation_exposed = True
                                            # print(f"{role}: {statement}")

                        print(f"[SUCCESS] Judgement: valid. Justification: {judgement.get('justification', 'N/A')}")
                        print(f"[*] Saved to {file_path}")
                        log_entry["final_status"] = "SUCCESS"
                        write_log(log_entry, LOG_FILE)
                        sleep(1)
                        break
                    else:
                        quality = judgement.get('label_quality', 'UNKNOWN') if judgement else 'UNKNOWN'
                        reason_text = judge_error or (judgement.get('justification') if judgement else 'No justification provided.')
                        print(f"[FAILURE] Judgement: {quality}. Reason: {reason_text}")
                        log_entry["final_status"] = f"JUDGE_REJECTED_{quality.upper()}"
                        write_log(log_entry, LOG_FILE)
                        sleep(2)
                else:
                    print(f"\n[CRITICAL] Failed to generate a valid file in {MAX_RETRIES_PER_FILE} attempts. Moving to next cycle.")

    print(f"\n--- Process Complete: {saved_count} conversation simulations saved. ---")


if __name__ == "__main__":
    main()
