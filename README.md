# Google Scholar Citation Scraper

A robust Python-based scraper that automatically extracts citation data from Google Scholar profiles and maintains up-to-date publication statistics through GitHub Actions automation.

## Features

- **Automated Scraping**: Uses the `scholarly` library to extract comprehensive publication data
- **GitHub Actions Integration**: Automatically runs weekly to keep data fresh
- **Comprehensive Error Handling**: Includes proxy support, retry mechanisms, and fallback strategies
- **Publication Keys**: Extracts unique publication identifiers (e.g., `hW23VKIAAAAJ:u-x6o8ySG0sC`)
- **Intermediate Results**: Saves progress during long scraping sessions to prevent data loss
- **Rate Limiting Protection**: Built-in delays and anti-detection measures
- **Data Validation**: Ensures data quality and handles edge cases

## Quick Start

### Prerequisites

- Python 3.9+
- Git repository with GitHub Actions enabled

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd <your-repo-name>
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Usage

#### Manual Scraping

Run the scraper locally with a Google Scholar user ID:

```bash
python scrape_scholar.py <scholar_user_id>
```

Example:
```bash
python scrape_scholar.py hW23VKIAAAAJ
```

This will generate a `gs_data.json` file containing all citation data.

#### Automated Scraping (GitHub Actions)

The scraper runs automatically every Sunday at 2 AM UTC via GitHub Actions. You can also:

1. **Manual Trigger**: Go to Actions tab → "Scrape Google Scholar Citations" → "Run workflow"
2. **Auto Trigger**: Pushes to main branch with changes to scraper files

Results are automatically committed to the `google-scholar` branch.

## Configuration

### Finding Your Scholar ID

Your Google Scholar user ID can be found in your profile URL:
```
https://scholar.google.com/citations?user=YOUR_USER_ID
```

### Workflow Customization

Edit `.github/workflows/scrape-scholar.yml` to:
- Change the schedule (modify the cron expression)
- Adjust timeout settings
- Modify the target branch name

## Output Format

The scraper generates a JSON file with the following structure:

```json
{
  "name": "Author Name",
  "affiliation": "Institution",
  "interests": ["Research Area 1", "Research Area 2"],
  "email_domain": "@institution.edu",
  "homepage": "https://example.com",
  "total_citations": 1234,
  "h_index": 20,
  "i10_index": 25,
  "citations_per_year": {
    "2020": 100,
    "2021": 150,
    "2022": 200
  },
  "publications": [
    {
      "title": "Paper Title",
      "authors": "Author List",
      "venue": "Conference/Journal",
      "year": 2023,
      "citations": 50,
      "pub_url": "https://paper-url.com",
      "key": "hW23VKIAAAAJ:u-x6o8ySG0sC"
    }
  ],
  "last_updated": "2024-01-01 12:00:00",
  "scraper_method": "scholarly"
}
```

## Technical Details

### Scholarly Library

This project uses the `scholarly` library (develop branch) which provides:
- Direct Google Scholar API access
- Built-in rate limiting
- Proxy support for CI environments
- Comprehensive publication metadata

### Error Handling

The scraper includes multiple layers of error handling:

1. **Proxy Configuration**: Automatically configures proxies for CI environments
2. **Retry Mechanisms**: Exponential backoff for failed requests
3. **Alternative Search**: Falls back to name-based search if ID lookup fails
4. **Data Freshness**: Uses existing data if recently updated (< 7 days)
5. **Graceful Degradation**: Returns fallback data if scraping completely fails

### Performance Optimization

- **Intermediate Saves**: Progress is saved every 10 publications
- **Smart Delays**: Different delay strategies for local vs CI execution
- **Timeout Protection**: 1-hour timeout to prevent hanging
- **Memory Efficiency**: Processes publications sequentially

## Troubleshooting

### Common Issues

1. **403 Forbidden Errors**: The scraper automatically handles these with proxy rotation
2. **Timeout Issues**: Increase the timeout in GitHub Actions or run locally
3. **Empty Publications**: Ensure the Scholar profile is public and has publications
4. **Rate Limiting**: The scraper includes built-in delays; avoid running too frequently

### Debug Mode

Run with verbose output to troubleshoot issues:
```bash
PYTHONUNBUFFERED=1 python scrape_scholar.py <user_id>
```

### GitHub Actions Debugging

Check the Actions tab for detailed logs. Common solutions:
- Ensure repository has proper permissions
- Verify the Scholar user ID is correct
- Check if the profile is publicly accessible

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source. Please ensure you comply with Google Scholar's terms of service when using this scraper.

## Disclaimer

This tool is for academic and research purposes. Please respect Google Scholar's rate limits and terms of service. The authors are not responsible for any misuse of this software.