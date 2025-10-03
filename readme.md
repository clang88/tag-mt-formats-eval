# TAG Format Evaluation

This repository contains the code and data for evaluating Terminology Augmented Generation (TAG) and various terminology formats for machine translation.


## Project Structure

```
├── Datasets/
│   └── WMT17/                    # WMT17 evaluation datasets and results
│       ├── *.tsv.de              # Translation outputs from different models
│       ├── *.csv                 # Translation timing data
│       ├── *.xlsx                # Evaluation results and analysis
│       └── Scripts/              # Data processing scripts
├── FinalNotebooks/               # Main analysis notebooks
│   ├── ModelPipeline.ipynb       # Translation pipeline and model setup
│   └── TranslationEvaluation.ipynb # Evaluation metrics and analysis
├── Open WebUI/
│   └── kalcium-python-client/    # Kalcium Python client library (see below)
│       ├── pyproject.toml
│       ├── README.md
│       ├── src/
│       │   └── kalcium_client/
│       │       ├── client.py
│       │       ├── kalcium_tag_functions.py
│       │       └── ...
│       └── ...
├── model_configs/                # Model configuration files
├── retrieval_functions/          # Scripts for translation with retrieval
└── readme.md                     # This file
```
## Kalcium Python Client

The Kalcium Python client is included in this repository under the `Open WebUI/kalcium-python-client/` folder. This client provides tools for interacting with Kalcium services, including terminology checking, translation, and more.

For installation and usage instructions, see `Open WebUI/kalcium-python-client/README.md`.


## Getting Started

### Prerequisites
- Python 3.7+
- Jupyter Notebook or VS Code with Jupyter extension
- Required packages: pandas, numpy, requests (see notebook imports)

### Usage

1. **Translation Pipeline** (`ModelPipeline.ipynb`)
   - Set up translation models
   - Configure system and user prompts
   - Generate translations and measure performance
   - Run cells sequentially from top to bottom

2. **Translation Evaluation** (`TranslationEvaluation.ipynb`)
   - Analyze translation speed and quality
   - Calculate BLEU scores and COMET metrics
   - Evaluate terminology adherence
   - Run cells sequentially from top to bottom

### Quick Start
1. Open the notebooks in your preferred environment
2. Install required dependencies when prompted
3. Follow the notebook instructions step by step
4. Results and visualizations will appear inline

## Data

The `Datasets/` folder contains experimental data including translation outputs from various models (GPT-4o, GPT-4o-mini, TAG) and evaluation metrics. Currently, only the Dataset from https://github.com/mtresearcher/terminology_dataset (Dinu et. al:2019) is present, but we will update the repo with our customer data dataset as soon as it is greenlit.


