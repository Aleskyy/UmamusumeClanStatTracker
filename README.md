# UmaClan Statistics Tracker

A Python tool to automatically download team statistics from Chronogenesis, extract player information, and send formatted reports to Discord.

## Features

- Downloads club statistics CSV from Chronogenesis
- Extracts player names and Friend IDs (FIDs) from club profile page
- Calculates daily, weekly, and monthly statistics for each player
- Sends formatted statistics reports to Discord via webhook
- Automatic file organization with date stamps

## Requirements

- Python 3.8+
- Chrome/Chromium browser (for Selenium)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/UmaClan.git
cd UmaClan
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create configuration file:
```bash
cp config.example.py config.py
```

4. Edit `config.py` and add your values:
```python
CIRCLE_ID = "your_circle_id_here"
DISCORD_WEBHOOK_URL = "your_discord_webhook_url_here"
```

## Usage

Run the script:
```bash
python ouaip.py
```

The script will:
1. Navigate to your club's Chronogenesis page
2. Download the statistics CSV
3. Extract player names and FIDs
4. Send a formatted report to Discord (if webhook URL is configured)

## Output Files

All files are saved in the `downloaded_files/` directory:

- `teamCSV_YYYY-MM-DD.csv` - Daily statistics export
- `player_names_YYYY-MM-DD.json` - Player name to FID mapping

## Configuration

### Circle ID

Your Circle ID can be found in the URL when viewing your club on Chronogenesis:
```
https://chronogenesis.net/club_profile?circle_id=YOUR_CIRCLE_ID
```

### Discord Webhook

Create a webhook in your Discord server:
1. Go to Server Settings > Integrations > Webhooks
2. Click "New Webhook"
3. Copy the webhook URL
4. Add it to your `config.py`

## Statistics Calculation

- **Daily Average**: Monthly total divided by number of days with data
- **Weekly Average**: Daily average multiplied by 7
- **Monthly Total**: Cumulative total from the CSV

Weekly requirement is set to 5,000,000 by default. Players meeting or exceeding this requirement are marked with ✅, others with ❌.

## License

MIT License

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
