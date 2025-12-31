# Net Gamma Exposure Tool

This tool calculates the Net Gamma Exposure (GEX) profile for options (specifically Nifty) and identifies the Zero Gamma Level (Flipping Point).

## Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### 1. Interactive Dashboard (Recommended)

To use the graphical interface with file upload and interactive charts:

```bash
streamlit run streamlit_app.py
```

*   Upload one or multiple `NIFTY_...csv` files.
*   Adjust the "Analysis Date" and "Spot Price" in the sidebar.
*   View the Net Gamma Profile chart and metrics.

### 2. Command Line Script

To run the analysis in the terminal and generate an HTML report:

```bash
python run_analysis.py
```

*   Place your CSV files (e.g., `NIFTY_2025-12-23_option_chain_....csv`) in the same directory.
*   The script will aggregate all matching files, calculate the profile, and save the chart to `gamma_profile.html`.

## Data Format

The tool supports:
1.  **Nifty Option Chain Format**: Files named like `NIFTY_YYYY-MM-DD_option_chain_YYYY-MM-DD-HH-MM-SS.csv`.
2.  **Standard CSV**: Columns `StrikePrice`, `OptionType`, `IV`, `OpenInterest`, `ExpirationDate`.
