#!/usr/bin/env python3
"""
Dataset Generation Script (Generic)

Generates synthetic scam conversations using LLM-based generation and validation.
This script is used to create e-commerce scam, tax scam, and neutral conversation datasets.

Usage:
    python dataset_generation/run_gen.py --scenario e-commerce_scam
    python dataset_generation/run_gen.py --scenario tax_scam

Note: TARGET_COUNT is set to 3 for artifact review. Increase for full dataset generation.
"""
import os
import sys
import json
import random
import re
import argparse
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

# Generation settings
TARGET_COUNT = 3  # Set low for artifact review - increase for full generation
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
    parser = argparse.ArgumentParser(description="Generate synthetic scam conversations")
    parser.add_argument("--scenario", type=str, required=True,
                        help="Scenario name (e.g., e-commerce_scam, tax_scam)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: auto-generated with timestamp)")
    parser.add_argument("--count", type=int, default=TARGET_COUNT,
                        help=f"Number of conversations to generate (default: {TARGET_COUNT})")
    args = parser.parse_args()
    
    # Setup paths
    scenario_file = SCENARIOS_DIR / f"{args.scenario}.json"
    if not scenario_file.exists():
        print(f"[CRITICAL] Scenario file not found: {scenario_file}")
        print(f"Available scenarios: {[f.stem for f in SCENARIOS_DIR.glob('*.json')]}")
        sys.exit(1)
    
    output_dir = args.output_dir or f"generated_{args.scenario}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log_file = f"generation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 1. Load all configurations and prompts
    print(f"--- Loading Scenario: {scenario_file} ---")
    config = load_json_file(scenario_file)
    print(f"--- Loading Prompts from: {PROMPT_DIR} ---")
    gen_template = load_prompt_template("generator.md")
    judge_template = load_prompt_template("judge.md")
    ideation_template = load_prompt_template("ideation_prompt.md")
    
    validated_conversations = []
    all_component_combinations = []
    saved_count = 0
    target_count = args.count
    
    # Store initial dynamic components
    initial_dynamic_components = {k: list(v) for k, v in config["dynamic_components"].items()}
    used_combinations = set()
    
    def calculate_initial_combinations():
        initial_user_personas = initial_dynamic_components.get("user_personas", [])
        initial_assistant_personas = initial_dynamic_components.get("assistant_personas", [])
        initial_style_options = initial_dynamic_components.get("style_options", [])
        return len(initial_user_personas) * len(initial_assistant_personas) * len(initial_style_options)

    total_initial_combinations = calculate_initial_combinations()
    print(f"Total initial combinations: {total_initial_combinations}")
    print(f"Target count: {target_count}")
    
    ideation_triggered = False
    
    print("\n--- Starting Generation ---")
    while saved_count < target_count:
        print(f"\n--- Cycle {saved_count + 1}/{target_count} ---")

        # Check if ideation should be triggered
        if (len(used_combinations) >= total_initial_combinations and not ideation_triggered and 
            config.get("ideation_controls", {}).get("enabled")):
            
            print("\n[*] Exhausted initial combinations. Running Ideation Step...")
            ideation_controls = config["ideation_controls"]
            components_to_generate = ideation_controls.get("components_to_generate", [])

            for component in components_to_generate:
                if component in config["dynamic_components"]:
                    print(f"Generating new ideas for: {component}")
                    newly_generated = generate_new_components(
                        ideation_template,
                        component,
                        config["dynamic_components"][component],
                        ideation_controls,
                        config["scenario_instructions"]
                    )
                    if newly_generated:
                        print(f"   -> Added {len(newly_generated)} new ideas for '{component}'")
                        config["dynamic_components"][component].extend(newly_generated)
                        used_combinations.clear()
            ideation_triggered = True

        for retry in range(MAX_RETRIES_PER_FILE):
            print(f"[*] Attempt {retry + 1}/{MAX_RETRIES_PER_FILE} for cycle {saved_count + 1}...")
            log_entry = {"timestamp": datetime.now().isoformat()}

            # Seeding step
            example_conversation_section = ""
            if config.get("seed_dialogue") and config["seed_dialogue"]:
                example_conversation = random.choice(config["seed_dialogue"])
                example_conversation_section = (
                    "\n\nHere is an example of a successful conversation that meets the criteria. "
                    "Use this as inspiration, but do not simply copy it. Create a new, unique conversation.\n"
                    f"```json\n{json.dumps(example_conversation, indent=2)}\n```\n"
                )
                log_entry["seeded_example"] = example_conversation
            
            # Component selection
            current_user_personas = config["dynamic_components"].get("user_personas", [])
            current_assistant_personas = config["dynamic_components"].get("assistant_personas", [])
            current_style_options = config["dynamic_components"].get("style_options", [])
            label_intensity = "subtle"

            if not all_component_combinations:
                for user in current_user_personas:
                    for assistant in current_assistant_personas:
                        for style in current_style_options:
                            all_component_combinations.append((user, assistant, style))
                random.shuffle(all_component_combinations)

            if all_component_combinations:
                selected_user, selected_assistant, selected_style = all_component_combinations.pop(0)
                combination_key = (selected_user, selected_assistant, selected_style)
                
                if not ideation_triggered:
                    if combination_key in used_combinations and len(used_combinations) < total_initial_combinations:
                        print("   -> Combination already used. Skipping.")
                        continue
                    used_combinations.add(combination_key)
            else:
                if not ideation_triggered and config.get("ideation_controls", {}).get("enabled"):
                    print("   -> All combinations exhausted. Triggering ideation...")
                    continue
                else:
                    print("   -> All combinations exhausted and no ideation available.")
                    break

            selected_components = {
                "user_personas": selected_user,
                "assistant_personas": selected_assistant,
                "style_options": selected_style,
                "label_intensity": label_intensity
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
                necessary_labels_text=format_dict_for_prompt(config["necessary_labels"]),
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
                write_log(log_entry, log_file)
                sleep(2)
                continue

            # Judging step
            judge_prompt = judge_template.format(
                scenario_instructions=config["scenario_instructions"],
                necessary_labels_text=format_dict_for_prompt(config["necessary_labels"]),
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
                file_path = os.path.join(output_dir, f"simulation_{saved_count:03d}.json")
                with open(file_path, "w") as f:
                    json.dump(conversation, f, indent=4)
                
                print(f"[SUCCESS] Judgement: valid. Justification: {judgement.get('justification', 'N/A')}")
                print(f"[*] Saved to {file_path}")
                log_entry["final_status"] = "SUCCESS"
                write_log(log_entry, log_file)
                sleep(1)
                break
            else:
                quality = judgement.get('label_quality', 'UNKNOWN') if judgement else 'UNKNOWN'
                reason_text = judge_error or (judgement.get('justification') if judgement else 'No justification provided.')
                print(f"[FAILURE] Judgement: {quality}. Reason: {reason_text}")
                log_entry["final_status"] = f"JUDGE_REJECTED_{quality.upper()}"
                write_log(log_entry, log_file)
                sleep(2)
        else:
            print(f"\n[CRITICAL] Failed to generate a valid file in {MAX_RETRIES_PER_FILE} attempts. Moving to next cycle.")

    print(f"\n--- Process Complete: {saved_count} conversation simulations saved to {output_dir} ---")


if __name__ == "__main__":
    main()
