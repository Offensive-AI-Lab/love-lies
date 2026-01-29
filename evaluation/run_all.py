#!/usr/bin/env python3
"""
Run all content moderation evaluators.

This is the main entry point for running evaluations. It can run all three
evaluators (OpenAI, Google, LLaMA Guard) or a specific one.

Usage:
    python evaluation/run_all.py                    # Run all evaluators
    python evaluation/run_all.py --evaluator openai # Run specific evaluator
    python evaluation/run_all.py --subset 10        # Test with subset
"""
import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
log = logging.getLogger(__name__)


def run_evaluator(name: str, script: Path, data_dir: Path, output_dir: Path, subset: int = None) -> bool:
    """
    Run a single evaluator script.
    
    Args:
        name: Display name for the evaluator
        script: Path to the evaluator script
        data_dir: Directory containing conversation data
        output_dir: Directory for output files
        subset: Optional subset size per category
        
    Returns:
        True if evaluation succeeded, False otherwise
    """
    output_file = output_dir / f"{name}_results.csv"
    
    log.info("")
    log.info("=" * 60)
    log.info(f"[{name.upper()}] Starting evaluation...")
    log.info("=" * 60)
    
    cmd = [
        sys.executable,
        str(script),
        "--data-dir", str(data_dir),
        "--output", str(output_file),
    ]
    
    if subset:
        cmd.extend(["--subset", str(subset)])
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            log.error(f"[{name.upper()}] Evaluation failed with exit code {result.returncode}")
            return False
        log.info(f"[{name.upper()}] Completed successfully")
        return True
    except Exception as e:
        log.error(f"[{name.upper()}] Error: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run content moderation evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Run all evaluators:
    python evaluation/run_all.py

  Run specific evaluator:
    python evaluation/run_all.py --evaluator openai

  Test with subset (5 conversations per category):
    python evaluation/run_all.py --subset 5
        """
    )
    
    parser.add_argument(
        "--evaluator",
        choices=["openai", "google", "llama", "all"],
        default="all",
        help="Which evaluator(s) to run (default: all)"
    )
    
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Directory containing conversation data (default: ./data)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./results"),
        help="Directory for output files (default: ./results)"
    )
    
    parser.add_argument(
        "--subset",
        type=int,
        default=None,
        help="Process only N conversations per category (for testing)"
    )
    
    args = parser.parse_args()
    
    # Validate data directory
    if not args.data_dir.exists():
        log.error(f"Error: Data directory not found: {args.data_dir}")
        return 1
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Define evaluators
    evaluators = {
        "openai": script_dir / "openai_eval.py",
        "google": script_dir / "google_eval.py",
        "llama": script_dir / "llama_eval.py",
    }
    
    # Determine which evaluators to run
    if args.evaluator == "all":
        to_run = list(evaluators.keys())
    else:
        to_run = [args.evaluator]
    
    # Check that scripts exist
    for name in to_run:
        if not evaluators[name].exists():
            log.error(f"Error: Script not found: {evaluators[name]}")
            return 1
    
    # Run evaluators
    log.info("Content Moderation Evaluation")
    log.info(f"Data directory: {args.data_dir}")
    log.info(f"Output directory: {args.output_dir}")
    if args.subset:
        log.info(f"Subset size: {args.subset} per category")
    
    results = {}
    for name in to_run:
        success = run_evaluator(
            name=name,
            script=evaluators[name],
            data_dir=args.data_dir,
            output_dir=args.output_dir,
            subset=args.subset
        )
        results[name] = success
    
    # Summary
    log.info("")
    log.info("=" * 60)
    log.info("Summary")
    log.info("=" * 60)
    
    for name, success in results.items():
        status = "✓ Success" if success else "✗ Failed"
        log.info(f"  {name}: {status}")
    
    log.info("")
    log.info(f"Results saved to: {args.output_dir}")
    
    # Return non-zero if any evaluator failed
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())

