# Corporate Bond Data Viewer

A Streamlit web application for visualizing corporate bond data from the JSDA website.

## Features

- Date selection UI for choosing a specific date
- Automatic fetching of corporate bond data from JSDA website
- Translation of Japanese column headers to English
- Interactive visualization of "Average Compound Yield" data
- Error handling for various scenarios

## Installation

```bash
# Clone the repository
git clone https://github.com/Daiperp/bond-data-viewer.git
cd bond-data-viewer

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
# Run the Streamlit application
streamlit run app.py
```

## Data Source

The application fetches data from the JSDA (Japan Securities Dealers Association) website:
https://market.jsda.or.jp/shijyo/saiken/baibai/baisanchi/
