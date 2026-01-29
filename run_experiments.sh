#!/bin/bash
# =============================================================================
# Romance-Baiting Content Filter Experiments - Automation Script
# =============================================================================
# This script automates the full evaluation pipeline for reproducibility.
#
# Usage:
#   ./run_experiments.sh              # Run all evaluations
#   ./run_experiments.sh --quick      # Quick test with subset
#   ./run_experiments.sh openai       # Run specific evaluator
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
DATA_DIR="./data"
RESULTS_DIR="./results"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
    if [ ! -f ".env" ]; then
        log_error ".env file not found!"
        log_error "Please copy .env.example to .env and add your API keys:"
        log_error "  cp .env.example .env"
        exit 1
    fi
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 not found!"
        exit 1
    fi
    log_info "Python: $(python3 --version)"
}

check_dependencies() {
    log_info "Checking dependencies..."
    python3 -c "import openai, requests, pandas, dotenv, torch, transformers" 2>/dev/null || {
        log_error "Missing dependencies. Please run: pip install -r requirements.txt"
        exit 1
    }
    log_info "Dependencies OK"
}

# -----------------------------------------------------------------------------
# Main Functions
# -----------------------------------------------------------------------------

run_all() {
    local subset_arg=""
    if [ "$1" == "--quick" ]; then
        subset_arg="--subset 5"
        log_info "Running in quick mode (5 conversations per category)"
    fi

    log_info "Running all evaluations..."
    log_info "Results will be saved to: $RESULTS_DIR"
    echo ""

    python3 evaluation/run_all.py --data-dir "$DATA_DIR" --output-dir "$RESULTS_DIR" $subset_arg
}

run_single() {
    local evaluator=$1
    log_info "Running $evaluator evaluation..."
    
    case $evaluator in
        openai)
            python3 evaluation/openai_eval.py --data-dir "$DATA_DIR" --output "$RESULTS_DIR/openai_results.csv"
            ;;
        google)
            python3 evaluation/google_eval.py --data-dir "$DATA_DIR" --output "$RESULTS_DIR/google_results.csv"
            ;;
        llama)
            python3 evaluation/llama_eval.py --data-dir "$DATA_DIR" --output "$RESULTS_DIR/llama_results.csv"
            ;;
        judge)
            local found_results=0
            for result_file in openai_results.csv google_results.csv llama_results.csv; do
                if [ -f "$RESULTS_DIR/$result_file" ]; then
                    log_info "Running judge evaluation on $result_file..."
                    python3 evaluation/judge_llm.py --input "$RESULTS_DIR/$result_file" --data-dir "$DATA_DIR"
                    found_results=1
                fi
            done
            if [ $found_results -eq 0 ]; then
                log_error "No evaluation results found. Run evaluations first."
                exit 1
            fi
            ;;
        *)
            log_error "Unknown evaluator: $evaluator"
            log_error "Valid options: openai, google, llama, judge"
            exit 1
            ;;
    esac
}

show_usage() {
    echo "Usage: $0 [OPTIONS] [EVALUATOR]"
    echo ""
    echo "Options:"
    echo "  --quick     Run with small subset for testing"
    echo "  --help      Show this help message"
    echo ""
    echo "Evaluators:"
    echo "  openai      Run OpenAI Moderation API evaluation"
    echo "  google      Run Google Perspective API evaluation"
    echo "  llama       Run LLaMA Guard 3 evaluation"
    echo "  judge       Run LLM judge on results"
    echo "  (none)      Run all evaluations"
    echo ""
    echo "Examples:"
    echo "  $0                  # Run all evaluations"
    echo "  $0 --quick          # Quick test"
    echo "  $0 openai           # Run OpenAI only"
    echo "  $0 judge            # Judge results"
}

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

main() {
    echo "=============================================="
    echo "Romance-Baiting Content Filter Experiments"
    echo "=============================================="
    echo ""

    # Parse arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --quick)
            check_env
            check_python
            check_dependencies
            run_all --quick
            ;;
        openai|google|llama|judge)
            check_env
            check_python
            check_dependencies
            run_single "$1"
            ;;
        "")
            check_env
            check_python
            check_dependencies
            run_all
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac

    echo ""
    log_info "Done!"
}

main "$@"

