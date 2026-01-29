#!/usr/bin/env python3
"""
Google Perspective API Evaluator.

Evaluates conversations using Google's Perspective API to detect toxic content.
Only assistant (scammer) messages are evaluated.

Usage:
    python evaluation/google_eval.py --data-dir ./data --output results/google_results.csv
"""
import argparse
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[Google] %(message)s",
)
logging.getLogger("urllib3").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API configuration
PERSPECTIVE_URL = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
TOXICITY_THRESHOLD = 0.5  # Flag if toxicity score >= this value


def get_api_key() -> str:
    """Get and validate API key from environment."""
    api_key = os.getenv("GOOGLE_PERSPECTIVE_API_KEY")
    if not api_key:
        log.error("GOOGLE_PERSPECTIVE_API_KEY not found in environment.")
        log.error("Please set it in your .env file or environment.")
        sys.exit(1)
    return api_key


def load_conversations(data_dir: Path) -> list:
    """
    Load all conversations from the data directory.
    
    Args:
        data_dir: Path to directory containing category subdirectories
        
    Returns:
        List of (category, filename, conversation) tuples
    """
    conversations = []
    
    for category_dir in sorted(data_dir.iterdir()):
        if not category_dir.is_dir():
            continue
            
        category = category_dir.name
        
        for json_file in sorted(category_dir.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract assistant messages only
                raw_conv = data.get("conversation", [])
                messages = []
                for item in raw_conv:
                    role = item.get("Role", "").lower()
                    text = item.get("Statement") or item.get("text") or ""
                    if text and role == "assistant":
                        messages.append(text)
                
                if messages:
                    conversations.append((category, json_file.name, messages))
                    
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"Skipping {json_file}: {e}")
                
    return conversations


def moderate_text(api_key: str, text: str, retries: int = 3) -> dict:
    """
    Send text to Google Perspective API.
    
    Args:
        api_key: Perspective API key
        text: Text to analyze
        retries: Number of retry attempts
        
    Returns:
        Dict with flagged status, categories, and scores
    """
    payload = {
        "comment": {"text": text},
        "requestedAttributes": {"TOXICITY": {}}
    }
    params = {"key": api_key}
    
    for attempt in range(retries):
        try:
            response = requests.post(
                PERSPECTIVE_URL,
                params=params,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            score = result["attributeScores"]["TOXICITY"]["summaryScore"]["value"]
            flagged = score >= TOXICITY_THRESHOLD
            
            return {
                "flagged": flagged,
                "categories": {"TOXICITY": flagged},
                "category_scores": {"TOXICITY": score},
            }
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit
                wait_time = 2 ** (attempt + 1)
                log.warning(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            elif attempt < retries - 1:
                wait_time = 2 ** attempt
                log.warning(f"API error (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                log.error(f"API error after {retries} attempts: {e}")
                return {"flagged": False, "categories": {}, "category_scores": {}}
                
        except Exception as e:
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                log.warning(f"Error (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                log.error(f"Error after {retries} attempts: {e}")
                return {"flagged": False, "categories": {}, "category_scores": {}}
    
    return {"flagged": False, "categories": {}, "category_scores": {}}


def evaluate_conversation(api_key: str, messages: list) -> dict:
    """
    Evaluate a conversation, stopping at first flagged message.
    
    Args:
        api_key: Perspective API key
        messages: List of assistant messages
        
    Returns:
        Dict with evaluation results
    """
    for idx, message in enumerate(messages):
        result = moderate_text(api_key, message)
        if result["flagged"]:
            return {
                "any_flagged": True,
                "first_flagged_index": idx,
                "flagged_content": message,
                "categories": result["categories"],
                "category_scores": result["category_scores"],
            }
    
    return {
        "any_flagged": False,
        "first_flagged_index": None,
        "flagged_content": "",
        "categories": {},
        "category_scores": {},
    }


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate conversations using Google Perspective API"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing conversation data"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/google_results.csv"),
        help="Output CSV file"
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=None,
        help="Process only N conversations per category"
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    if not args.data_dir.exists():
        log.error(f"Data directory not found: {args.data_dir}")
        return 1
    
    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Get API key
    api_key = get_api_key()
    log.info("API key loaded")
    
    # Load conversations
    conversations = load_conversations(args.data_dir)
    log.info(f"Loaded {len(conversations)} conversations")
    
    # Apply subset if specified
    if args.subset:
        by_category = {}
        for cat, fname, msgs in conversations:
            by_category.setdefault(cat, []).append((cat, fname, msgs))
        
        conversations = []
        for cat_list in by_category.values():
            conversations.extend(cat_list[:args.subset])
        
        log.info(f"Using subset: {len(conversations)} conversations")
    
    # Process conversations
    log.info(f"Processing {len(conversations)} conversations...")
    
    start_time = time.time()
    
    results = []
    stats = {}
    
    for i, (category, filename, messages) in enumerate(tqdm(conversations, desc="Evaluating")):
        # Evaluate
        result = evaluate_conversation(api_key, messages)
        
        # Update stats
        stats.setdefault(category, {"total": 0, "flagged": 0})
        stats[category]["total"] += 1
        if result["any_flagged"]:
            stats[category]["flagged"] += 1
        
        # Store result
        results.append({
            "topic": category,
            "filename": filename,
            "any_flagged": result["any_flagged"],
            "first_flagged_index": result["first_flagged_index"] if result["first_flagged_index"] is not None else "",
            "flagged_content": result.get("flagged_content", ""),
            "categories": json.dumps(result["categories"]),
            "category_scores": json.dumps(result["category_scores"]),
        })
        
        # Progress update
        # if (i + 1) % 50 == 0 or (i + 1) == len(conversations):
        #     log.info(f"Progress: {i + 1}/{len(conversations)}")
        
        # Rate limiting
        time.sleep(1.1)  # Ensure we respect 1 req/sec limit + buffer
    
    end_time = time.time()
    duration = end_time - start_time
    log.info(f"Processed {len(conversations)} conversations in {duration:.2f}s (Avg: {len(conversations)/duration:.2f} conv/s)")
    
    # Write results
    fieldnames = ["topic", "filename", "any_flagged", "first_flagged_index", "flagged_content", "categories", "category_scores"]
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    log.info(f"Results saved to: {args.output}")
    
    # Print summary
    log.info("")
    log.info("Summary:")
    total_all = sum(s["total"] for s in stats.values())
    flagged_all = sum(s["flagged"] for s in stats.values())
    
    for category in sorted(stats.keys()):
        s = stats[category]
        pct = (s["flagged"] / s["total"] * 100) if s["total"] > 0 else 0
        log.info(f"  {category}: {s['flagged']}/{s['total']} flagged ({pct:.1f}%)")
    
    overall_pct = (flagged_all / total_all * 100) if total_all > 0 else 0
    log.info(f"  Overall: {flagged_all}/{total_all} flagged ({overall_pct:.1f}%)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
