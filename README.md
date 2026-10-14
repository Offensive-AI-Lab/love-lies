# Love, Lies, and Language Models: Investigating AI’s Role in Romance-Baiting Scams - Content Filter Experiments

**Project page:** https://offensive-ai-lab.com/love-lies/ · **Paper:** https://www.usenix.org/conference/usenixsecurity26/presentation/gressel


This artifact accompanies the paper **"Love, Lies, and Language Models: Investigating AI's Role in Romance-Baiting Scams"** published to USENIX Security 2026.

## Overview

This artifact evaluates how well commercial content moderation systems detect **romance-baiting scams** compared to other scam types (e-commerce fraud, tax scams) and benign conversations.

We test three content moderation systems:
| Moderator | Type | Provider |
|-----------|------|----------|
| OpenAI Moderation API | Cloud API | OpenAI |
| Google Perspective API | Cloud API | Google |
| LLaMA Guard 3 (8B) | Local Model | Meta |

### Key Finding

Romance-baiting conversations evade detection at significantly higher rates than other scam types, highlighting a critical gap in current content moderation systems.

---

## Repository Structure

```
.
├── README.md                  # This file
├── LICENSE                    # CC BY 4.0 (code and dataset)
├── requirements.txt           # Python dependencies (pinned versions)
├── environment.yml            # Conda environment file
├── .env.example              # Template for API keys
│
├── data/                     # Evaluation dataset (1000 conversations)
│   ├── romance_baiting/      # 250 romance-baiting scam conversations
│   ├── e-commerce/           # 250 e-commerce scam conversations
│   ├── tax_scam/             # 250 tax scam conversations
│   └── neutral/              # 250 benign conversations
│
├── run_experiments.sh          # Main automation script
├── evaluation/               # Evaluation scripts
│   ├── run_all.py           # Main entry point - runs all evaluators
│   ├── openai_eval.py       # OpenAI Moderation API evaluator
│   ├── google_eval.py       # Google Perspective API evaluator
│   ├── llama_eval.py        # LLaMA Guard 3 evaluator
│   └── judge_llm.py         # LLM judge for false positive analysis
│
├── dataset_generation/       # Scripts used to generate the dataset (see dataset_generation/README.md)
│   ├── README.md            # Documentation for dataset generation
│   ├── run_gen.py           # Generic scam conversation generator
│   ├── run_gen_romance_baiting.py  # Romance-baiting generator
│   ├── prompts/             # LLM prompts for generation
│   └── scenarios/           # Scenario configurations
│
└── expected_results/         # Reference results from our experiments
    ├── openai.csv
    ├── google.csv
    └── llama.csv
```

---

## Requirements

### Hardware
- **Minimum (API-based evaluation):** Any machine with internet access
- **For LLaMA Guard:** GPU with ≥16GB VRAM
- **Disk space:** ~20GB for LLaMA Guard model weights

### Software
- Python 3.9–3.12 (PyTorch 2.3.0 does not support Python 3.13+)
- CUDA 11.8+ (for LLaMA Guard on NVIDIA GPUs)

### Tested Environments
| OS | Python | GPU | Status |
|----|--------|-----|--------|
| Ubuntu 22.04 LTS | 3.12 | NVIDIA RTX6000 (40GB) | ✅ Verified |
---

## Installation

### Step 1: Clone and Setup Environment

```bash
# Option 1: Conda 
conda env create -f environment.yml
conda activate scam-moderator-eval

# Option 2: venv + uv (faster, modern dependency resolver)
# If you don't have uv: pip install uv
uv venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install -r requirements.txt

# Option 3: Standard venv + pip
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

*Note: All three options produce equivalent environments. The Conda option pins Python 3.9 and resolves PyTorch/CUDA binaries automatically; Options 2 and 3 require Python 3.9+ to already be installed. You only need to use one of the options above.*

### Step 2: Configure API Keys

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
```

Required API keys:

| Key | Required For | How to Obtain |
|-----|--------------|---------------|
| `OPENAI_API_KEY` | OpenAI Moderation, Judge LLM | https://platform.openai.com/api-keys |
| `GOOGLE_PERSPECTIVE_API_KEY` | Google Perspective | https://developers.perspectiveapi.com |
| `HUGGINGFACE_TOKEN` | LLaMA Guard | https://huggingface.co/settings/tokens |

**Note for LLaMA Guard:** You must accept Meta's license agreement at https://huggingface.co/meta-llama/Llama-Guard-3-8B before using your token.

### Step 3: Verify Installation

```bash
# Run a minimal test (5 conversations per category)
./run_experiments.sh --quick
```

Expected output:
```
[OpenAI] Starting evaluation...
[OpenAI] Processing 20 conversations...
[OpenAI] Results saved to: results/openai_results.csv
[OpenAI] Summary:
  romance_baiting: 0/5 flagged (0.0%)
  e-commerce: 2/5 flagged (40.0%)
  tax_scam: 3/5 flagged (60.0%)
  neutral: 0/5 flagged (0.0%)
```

---

## Usage

### Quick Start: Run All Evaluations

```bash
# Make the script executable
chmod +x run_experiments.sh

# Run all three evaluators on the full dataset
./run_experiments.sh

# Results will be saved to results/ directory
```

### Run Individual Evaluators

```bash
# OpenAI Moderation API (~12 minutes, ~$0.10)
./run_experiments.sh openai

# Google Perspective API (~5+ hours, free tier available)
./run_experiments.sh google

# LLaMA Guard 3 (~1 hour depending on GPU)
./run_experiments.sh llama
```

### Run with Subset (for Testing)

```bash
# Process only 5 conversations per category
./run_experiments.sh --quick
```

### Judge LLM (False Positive Analysis)

We observed that some of the flagged conversations were false positives after running the evaluations with the moderators, so we used a judge LLM to analyze all flagged content from all datasets for false positives:

```bash
./run_experiments.sh judge
```

The judge evaluates the `flagged_content` from all flagged conversations to determine true positives (actually harmful) vs false positives (benign but flagged).

---

## Reproducing Paper Results

### Claims and Reproduction Steps

| Claim | Section | Command | Expected Time | Expected Output |
|-------|---------|---------|---------------|-----------------|
| Romance-baiting detection rates | §5.2.2 | `./run_experiments.sh` | ~13 hours | See Table 2 |
| False positive analysis | §5.2.2 | `./run_experiments.sh judge` | ~30 min | See Table 2 |

### Expected Results Summary

After running all evaluations, you should observe detection rates similar to:

| Dataset | OpenAI | Google | LLaMA Guard |
|---------|--------|--------|-------------|
| Romance Baiting | ~18.8% | ~1.6% | ~2% |
| E-commerce Scam | ~0% | ~0% | ~75.6% |
| Tax Scam | ~0% | ~0% | ~97.6% |
| Neutral | ~0.4% | ~0% | ~0.4% |

**Note:** Exact numbers may vary slightly due to API updates and model non-determinism.

### Comparing Your Results

Reference results from our experiments are provided in `expected_results/` as CSV files. Your results (in `results/`) will be CSV files that can be compared using any spreadsheet application or pandas:

```bash
# Your results will be in results/
ls results/

# Reference results are in expected_results/
ls expected_results/
```

```python
# Quick comparison script
import pandas as pd

# Load your results
your_results = pd.read_csv("results/openai_results.csv")
expected = pd.read_csv("expected_results/openai.csv")

# Compare detection rates by category
print(your_results.groupby("topic")["any_flagged"].mean())
```

---

## Output Format

Results are saved as CSV files with the following columns:

| Column | Description |
|--------|-------------|
| `topic` | Category (romance_baiting, e-commerce, tax_scam, neutral) |
| `filename` | Source conversation file |
| `any_flagged` | Whether any turn was flagged (True/False) |
| `first_flagged_index` | Index of first flagged turn (if any) |
| `flagged_content` | The actual text content that was flagged |
| `categories` | Flagged categories (JSON) |
| `category_scores` | Category confidence scores (JSON) |

---

## Resource Estimates

> [!IMPORTANT]
> **Plan for a long run.** A full end-to-end evaluation takes approximately **14–15 hours** total, dominated by the Google Perspective API (rate-limited to ~12 hours). We strongly recommend running evaluators individually and overnight. Use `--quick` (5 conversations/category, ~5 minutes total) to verify your setup before committing to the full run.

| Evaluator | Command | Est. Time (full) | Est. Time (--quick) | API Cost | GPU Memory |
|-----------|---------|-----------------|---------------------|----------|------------|
| OpenAI Moderation | `./run_experiments.sh openai` | ~12 min | ~1 min | ~$0.50 | N/A |
| Google Perspective | `./run_experiments.sh google` | ~12 hours | ~5 min | Free (rate-limited) | N/A |
| LLaMA Guard 3 | `./run_experiments.sh llama` | ~1 hour | ~5 min | Free | 16GB+ VRAM |
| Judge LLM | `./run_experiments.sh judge` | ~30 min | N/A | ~$2.00 | N/A |
| **All (sequential)** | `./run_experiments.sh` | **~14 hours** | **~5 min** | **~$2.50** | **16GB+** |

*Timings measured on Ubuntu 22.04, NVIDIA RTX6000 (40GB), Python 3.12. Google Perspective time is dominated by free-tier rate limits (1 QPS). Your results may vary based on API quota and GPU.*

---

## Troubleshooting

### Common Issues
**"API key not found"**
- Ensure `.env` file exists and contains the required API keys
- Verify that the environment variable names match those expected by the script

**"Rate limit exceeded" (Google)**
- The Perspective API has rate limits; the script includes automatic backoff
- For faster processing, request a quota increase

**"CUDA out of memory" (LLaMA Guard)**
- Reduce batch size or use a GPU with more memory
- On Apple Silicon, ensure enough swap space

**"Model access denied" (LLaMA Guard)**
- Accept the license at https://huggingface.co/meta-llama/Llama-Guard-3-8B
- Verify your HuggingFace token has read access

### Getting Help

If you encounter issues reproducing our results, please:
1. Check the troubleshooting section above
2. Ensure all dependencies are correctly installed
3. Open an issue with your error log and environment details

---

## Dataset Generation (Optional)

The dataset used in our experiments is pre-generated and available in `data/`. However, we provide the generation scripts for reproducibility.

> **Warning:** Dataset generation incurs API costs and significant time. The scripts are configured with `TARGET_COUNT=3` by default to avoid accidental large-scale generation. **Generating the full dataset takes approximately 20–25 hours and costs ~$35–60 in OpenAI API credits.** The pre-generated dataset in `data/` is sufficient to reproduce all evaluation results.

### Runtime Estimates (Full Dataset)

| Script | Target | Est. Time | API Cost |
|--------|--------|-----------|----------|
| `run_gen.py --scenario e-commerce_scam --count 250` | 250 conversations | ~2–3 hours | ~$7–12 |
| `run_gen.py --scenario tax_scam --count 250` | 250 conversations | ~2–3 hours | ~$7–12 |
| `run_gen.py --scenario neutral --count 250` | 250 conversations | ~2–3 hours | ~$7–12 |
| `run_gen_romance_baiting.py` | 250 conversation threads (7 days each) | ~14–16 hours | ~$15–25 |
| **Total** | **1,000 conversations** | **~20–25 hours** | **~$35–60** |

See [`dataset_generation/README.md`](dataset_generation/README.md) for full details on API call counts and generation mechanics.

### Quick Start

```bash
# Generate a few e-commerce scam conversations (for testing, ~$0.10)
python dataset_generation/run_gen.py --scenario e-commerce_scam --count 3

# Generate romance-baiting conversations (3 days only by default)
python dataset_generation/run_gen_romance_baiting.py
```

### Available Scenarios

| Scenario | Script | Description |
|----------|--------|-------------|
| `e-commerce_scam` | `run_gen.py` | Fake product/payment scams |
| `tax_scam` | `run_gen.py` | IRS/tax authority impersonation |
| `romance_baiting` | `run_gen_romance_baiting.py` | Multi-day relationship scams |

---

## License

All code and data are released under the Creative Commons Attribution 4.0 International License (CC BY 4.0).

See [LICENSE](LICENSE) for full details.

---
