# Dataset Generation Scripts

This folder contains the scripts used to generate the synthetic conversation datasets used in our experiments.

> **Note:** The datasets have already been generated and are available in the `data/` directory. These scripts are provided for reproducibility and transparency.

## Overview

We use a **generate-and-judge** approach:
1. An LLM generates a conversation based on scenario configurations and prompts
2. A judge LLM evaluates whether the conversation meets quality criteria
3. Only validated conversations are saved to the dataset

## Scripts

### `run_gen.py` - Generic Scam Generation

Generates e-commerce scam, tax scam, and neutral conversation datasets.

```bash
# Generate e-commerce scam conversations
python dataset_generation/run_gen.py --scenario e-commerce_scam

# Generate tax scam conversations  
python dataset_generation/run_gen.py --scenario tax_scam

# Specify output directory and count
python dataset_generation/run_gen.py --scenario e-commerce_scam --output-dir ./my_output --count 10
```

**Arguments:**
| Argument | Description | Default |
|----------|-------------|---------|
| `--scenario` | Scenario name (required) | - |
| `--output-dir` | Output directory | Auto-generated with timestamp |
| `--count` | Number of conversations | 3 (for artifact review) |

### `run_gen_romance_baiting.py` - Romance-Baiting Generation

Generates multi-day romance-baiting scam conversations. Each conversation simulates a week-long interaction with evolving relationship dynamics.

```bash
python dataset_generation/run_gen_romance_baiting.py
```

This script generates conversations across multiple "days" for each victim-scammer pair, simulating the gradual trust-building process characteristic of romance-baiting scams.

## Directory Structure

```
dataset_generation/
├── README.md                    # This file
├── run_gen.py                   # Generic scam generation
├── run_gen_romance_baiting.py   # Romance-baiting generation
├── prompts/                     # LLM prompt templates
│   ├── generator.md             # Conversation generation prompt
│   ├── judge.md                 # Quality validation prompt
│   └── ideation_prompt.md       # Component ideation prompt
└── scenarios/                   # Scenario configurations
    ├── e-commerce_scam.json     # E-commerce scam settings
    ├── tax_scam.json            # Tax scam settings
    ├── romance_baiting.json     # Romance-baiting settings
    └── victim_background.json   # Victim persona profiles
```

## Prerequisites

1. **API Key:** Set `OPENAI_API_KEY` in the `.env` file at the repository root:
   ```bash
   # From repository root
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

2. **Dependencies:** Ensure all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### Scenario Files (`scenarios/`)

Each scenario JSON file contains:
- `scenario_instructions`: High-level description of the scam type
- `dynamic_components`: Variable elements (personas, styles, topics)
- `necessary_labels`: Required elements in every conversation
- `sufficient_labels`: Optional elements that may appear
- `dialogue_controls`: Turn limits and role definitions
- `generator_model`: LLM model for generation
- `judge_model`: LLM model for validation
- `seed_dialogue`: Example conversations for few-shot learning

### Prompt Templates (`prompts/`)

- **generator.md**: Template for generating conversations
- **judge.md**: Template for validating conversation quality
- **ideation_prompt.md**: Template for generating new scenario components

## Generation Parameters

For artifact review, generation counts are set low to avoid accidentally generating large datasets and incurring API costs.

To generate the full dataset (250 conversations per category), modify the scripts:

```python
# In run_gen.py
TARGET_COUNT = 250

# In run_gen_romance_baiting.py
TARGET_DAYS = 7                # 7 days of conversation per thread
TARGET_CONVERSATIONS = None    # Generate all (personas × 5 = 250 threads)
```

## Output Format

Generated conversations are saved as JSON files:

```json
{
  "conversation": [
    {
      "Role": "assistant",
      "Statement": "Hey there! I noticed we matched..."
    },
    {
      "Role": "user",
      "Statement": "Hi! Yeah, I liked your profile..."
    }
  ]
}
```

## Runtime Estimates

Each conversation requires **2 GPT-4.1 API calls** (one generator, one judge). Calls are made sequentially with 1–2 second sleeps between attempts. Some conversations are rejected by the judge and retried, adding ~30–50% overhead.

### Ideation Step

When the script exhausts all initial persona/style combinations, it triggers an **ideation step** — calling the LLM once per component to brainstorm new variants, then continuing generation with the expanded pool. This adds a small number of extra calls:

### Per-Script Estimates

| Script | Conversations | API Calls (est.) | Est. Time | API Cost |
|--------|-------------|-----------------|-----------|----------|
| `run_gen.py --scenario e-commerce_scam --count 250` | 250 | ~650 | ~2–3 hours | ~$7–12 |
| `run_gen.py --scenario tax_scam --count 250` | 250 | ~653 (+3 ideation) | ~2–3 hours | ~$7–12 |
| `run_gen.py --scenario neutral --count 250` | 250 | ~653 (+3 ideation) | ~2–3 hours | ~$7–12 |
| `run_gen_romance_baiting.py` (7 days × 250 chats) | 1,750 day-files | ~4,500 | ~14–16 hours | ~$15–25 |
| **Full dataset (all scripts)** | **1,000 conversations** | **~6,460** | **~20–25 hours** | **~$35–60** |

> **Note:** Romance-baiting is the bottleneck — it generates 7 sequential day-files per conversation thread, where each day is an independent API call pair. All 7 days must be generated in order for a single conversation thread.

The default `TARGET_COUNT=3` generates only 3 conversations (or 3 days for romance-baiting), costing approximately **$0.10–0.30** and completing in **under 2 minutes**.

## Troubleshooting

**"OPENAI_API_KEY not found"**
- Ensure `.env` file exists in the repository root
- Verify the key is set correctly: `OPENAI_API_KEY=sk-...`

**"Scenario file not found"**
- Check that you're running from the repository root
- Verify the scenario name matches a file in `scenarios/`

**JSON decode errors**
- The LLM occasionally produces malformed JSON
- The scripts automatically retry failed generations

**Rate limiting**
- The scripts include automatic delays between API calls
- For large-scale generation, consider adding longer delays

