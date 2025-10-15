---
title: NYC Voucher Housing Navigator
emoji: 🏠
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.42.0"
app_file: app.py
pinned: false
---

# NYC Voucher-Friendly Housing Collector

A Python tool for collecting housing listings that accept housing vouchers (Section 8, CityFHEPS, etc.) in New York City. This tool uses legitimate data sources and APIs rather than web scraping.

## Features

- Collects listings from official sources:
  - HUD Affordable Housing Database
  - NYCHA (NYC Housing Authority)
  - Legitimate rental APIs
- Filters for voucher-friendly listings
- Respects terms of service and anti-scraping measures
- Provides manual data collection guidance

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/voucher-housing-collector.git
cd voucher-housing-collector
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the main script:
```bash
python legitimate_collector.py
```

This will:
1. Collect listings from all configured sources
2. Filter for voucher-friendly listings
3. Display results in a readable format
4. Show manual data collection options

## Data Sources

The tool uses the following legitimate sources:
- HUD Affordable Housing Database
- NYCHA Property Information
- NYC Housing Connect
- Section 8 Housing Choice Voucher Program

## Why Not Scraping?

Web scraping platforms like Craigslist is problematic because:
- Strong anti-scraping measures (403 Forbidden errors)
- Rate limiting and IP blocking
- Terms of service prohibit automated access
- Captcha challenges
- Dynamic content loading that breaks parsers

Instead, this tool focuses on legitimate data sources and APIs that explicitly allow programmatic access.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
