# Swing Trading Tool

Swing Trading Intelligence Platform for Indian equities — analyzes market data, technical indicators, financial metrics, sector strength, and trading signals to identify high-potential swing trading opportunities with clear, data-driven explanations.

## Table of Contents

- [Features](#features)
- [Architecture & Tech Stack](#architecture--tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Examples](#examples)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- Ingests and preprocesses historical and intraday market data for Indian equities
- Computes technical indicators (moving averages, RSI, MACD, Bollinger Bands, etc.)
- Evaluates fundamental and financial metrics when available
- Ranks and filters opportunities by multi-factor scoring (trend, momentum, volume, fundamentals)
- Generates clear trading signals and human-readable explanations for each recommendation
- Supports backtesting and basic performance analytics for strategy verification

## Architecture & Tech Stack

- Language: Python
- Data sources: (configurable) — historical OHLC, volume, corporate actions, and fundamentals
- Core libraries: pandas, numpy, TA-lib / ta, matplotlib / plotly (for charts), scikit-learn (optional for models)
- Optional: database (SQLite/Postgres) or local CSV storage for time-series

## Installation

1. Clone the repository:

   git clone https://github.com/vignesh19807/swing-trading-tool.git
   cd swing-trading-tool

2. Create a virtual environment and install dependencies:

   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate  # Windows

   pip install -r requirements.txt

3. (Optional) Install TA libraries that may need system deps (for TA-Lib):

   # On Debian/Ubuntu
   sudo apt-get install build-essential libtool libffi-dev python3-dev libatlas-base-dev

   # Then install Python wheel
   pip install ta-lib

If you do not use TA-Lib, the `ta` Python package is a lightweight alternative:

   pip install ta

## Configuration

- Create a configuration file (example: config.yaml or .env) to set data source credentials, symbols list, timeframe, lookback window, and output directories.
- Example config keys:
  - data_source: local_csv | api_provider_name
  - symbols: ["RELIANCE", "TCS", "HDFCBANK"]
  - timeframe: 1d | 1h | 15m
  - start_date / end_date
  - output_dir

## Usage

- Preprocess/ingest data:

  python scripts/ingest_data.py --config config.yaml

- Run analysis / generate signals:

  python scripts/generate_signals.py --config config.yaml

- Backtest a strategy:

  python scripts/backtest.py --strategy strategies/default_strategy.py --config config.yaml

- Visualize results (example):

  python scripts/plot_results.py --input results/latest_signals.csv

Replace script names above with the actual entry points in the repository.

## Examples

- To analyze a list of symbols for the past 6 months on daily timeframe:

  1. Update config.yaml with symbols, timeframe: "1d", and start_date/end_date
  2. Run: `python scripts/ingest_data.py --config config.yaml`
  3. Run: `python scripts/generate_signals.py --config config.yaml`
  4. Inspect `outputs/` for ranked opportunities and explanations

## Development

- Run tests (if available):

  pytest

- Linting and formatting:

  pip install black flake8 isort
  black .

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch for your change
3. Make changes and add tests if applicable
4. Open a pull request describing your changes

## License

This project does not include a license file currently. Add a LICENSE file (for example, MIT) if you want to make the project open-source.
