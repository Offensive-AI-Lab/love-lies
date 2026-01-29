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

For artifact review, `TARGET_COUNT` is set to **3** to avoid accidentally generating large datasets and incurring API costs.

To generate the full dataset (250 conversations per category), modify the scripts:

```python
# In run_gen.py
TARGET_COUNT = 250

# In run_gen_romance_baiting.py  
TARGET_COUNT = 7  # 7 days of conversation per victim
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

## API Costs

Estimated costs for generating the full dataset (~1000 conversations):
- Generation: ~$15-25 (GPT-4 level models)
- Judging: ~$5-10

The default `TARGET_COUNT=3` setting generates only 3 conversations, costing approximately $0.10-0.20.

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

