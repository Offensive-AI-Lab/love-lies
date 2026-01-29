#!/usr/bin/env python3
"""
OpenAI Moderation API Evaluator.

Evaluates conversations using OpenAI's Moderation API to detect harmful content.
Only assistant (scammer) messages are evaluated.

Usage:
    python evaluation/openai_eval.py --data-dir ./data --output results/openai_results.csv
"""
import argparse
import asyncio
import csv
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Tuple, Dict, Any

from tqdm.asyncio import tqdm_asyncio

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[OpenAI] %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def get_client() -> AsyncOpenAI:
    """Initialize and return OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.error("OPENAI_API_KEY not found in environment.")
        log.error("Please set it in your .env file or environment.")
        sys.exit(1)
    return AsyncOpenAI(api_key=api_key)


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


async def moderate_text(client: AsyncOpenAI, text: str, retries: int = 5) -> dict:
    """
    Send text to OpenAI Moderation API.
    
    Args:
        client: OpenAI client instance
        text: Text to moderate
        retries: Number of retry attempts
        
    Returns:
        Dict with flagged status, categories, and scores
    """
    for attempt in range(retries):
        try:
            response = await client.moderations.create(
                model="omni-moderation-latest",
                input=text,
            )
            result = response.results[0]
            return {
                "flagged": result.flagged,
                "categories": dict(result.categories),
                "category_scores": dict(result.category_scores),
            }
        except Exception as e:
            if attempt < retries - 1:
                # Exponential backoff with jitter could be better, but simple is fine
                wait_time = (2 ** attempt) + 0.1
                if "429" in str(e):
                     log.warning(f"Rate limited (attempt {attempt + 1}). Retrying in {wait_time}s...")
                else: 
                     log.warning(f"API error (attempt {attempt + 1}): {e}. Retrying in {wait_time}s...")
                
                await asyncio.sleep(wait_time)
            else:
                log.error(f"API error after {retries} attempts: {e}")
                return {"flagged": False, "categories": {}, "category_scores": {}}


async def evaluate_conversation(
    client: AsyncOpenAI, 
    messages: List[str], 
    semaphore: asyncio.Semaphore
) -> Dict[str, Any]:
    """
    Evaluate a conversation, stopping at first flagged message.
    
    Args:
        client: OpenAI client instance
        messages: List of assistant messages
        semaphore: Concurrency limiter
        
    Returns:
        Dict with evaluation results
    """
    # Just need one semaphore acquisition for the serial processing of this conversation
    # Or should we acquire per request? 
    # Acquiring per request allows inter-conversation interleaving which is better for overall throughput if conversations vary in length.
    
    for idx, message in enumerate(messages):
        async with semaphore:
            result = await moderate_text(client, message)
        
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


async def process_conversations(
    conversations: List[Tuple[str, str, List[str]]], 
    client: AsyncOpenAI,
    max_concurrency: int = 50
) -> List[Dict[str, Any]]:
    """
    Process all conversations concurrently.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = []
    
    for category, filename, messages in conversations:
        task = asyncio.create_task(evaluate_conversation(client, messages, semaphore))
        tasks.append((category, filename, task))
    
    results = []
    total = len(tasks)
    
    # Process tasks as they complete to show progress
    pending = [t[2] for t in tasks]
    completed_count = 0
    
    # We need to map back results to metadata, so let's just await all and zip
    # But for progress bar, we can use as_completed on a wrapped version
    
    log.info(f"Processing {total} conversations with concurrency {max_concurrency}...")
    
    start_time = time.time()
    
    # Execute all tasks with progress bar
    task_results = await tqdm_asyncio.gather(*[t[2] for t in tasks], desc="Evaluating")
    
    end_time = time.time()
    duration = end_time - start_time
    log.info(f"Processed {total} conversations in {duration:.2f}s (Avg: {total/duration:.2f} conv/s)")

    for i, res in enumerate(task_results):
        category, filename, _ = tasks[i]
        results.append({
            "topic": category,
            "filename": filename,
            "any_flagged": res["any_flagged"],
            "first_flagged_index": res["first_flagged_index"] if res["first_flagged_index"] is not None else "",
            "flagged_content": res.get("flagged_content", ""),
            "categories": json.dumps(res["categories"]),
            "category_scores": json.dumps(res["category_scores"]),
        })

    return results


async def async_main() -> int:
    """Async main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate conversations using OpenAI Moderation API"
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
        default=Path("results/openai_results.csv"),
        help="Output CSV file"
    )
    parser.add_argument(
        "--subset",
        type=int,
        default=None,
        help="Process only N conversations per category"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=25,
        help="Max concurrent API requests"
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    if not args.data_dir.exists():
        log.error(f"Data directory not found: {args.data_dir}")
        return 1
    
    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize client
    client = get_client()
    log.info("API client initialized")
    
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
    results = await process_conversations(conversations, client, args.concurrency)
    
    # Calculate stats
    stats = {}
    for res in results:
        cat = res["topic"]
        stats.setdefault(cat, {"total": 0, "flagged": 0})
        stats[cat]["total"] += 1
        if res["any_flagged"]:
            stats[cat]["flagged"] += 1

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


def main():
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
