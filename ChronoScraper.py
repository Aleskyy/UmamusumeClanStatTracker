import os
import json
import csv
import requests
from datetime import datetime
from seleniumbase import SB
from bs4 import BeautifulSoup

try:
    from config import CIRCLE_ID, DISCORD_WEBHOOK_URL
except ImportError:
    CIRCLE_ID = None
    DISCORD_WEBHOOK_URL = None
    print("Warning: config.py not found. Please create it from config.example.py")


def download_club_csv(sb, circle_id, download_dir):
    """Navigate to club page and download CSV"""
    club_url = f"https://chronogenesis.net/club_profile?circle_id={circle_id}"
    print(f"Navigating to: {club_url}")

    sb.open(club_url)
    sb.sleep(3)

    csv_file_path = None
    try:
        export_button = sb.find_element('div.save-button.expanded[title="Export as .csv"]')
        print("Export button found, clicking...")
        export_button.click()
        sb.sleep(3)

        csv_file_path = rename_latest_download(download_dir)
        print("Download complete!")

    except Exception as e:
        print(f"Error clicking export button: {e}")

    json_file_path = fetch_player_names(sb, download_dir)

    return csv_file_path, json_file_path


def rename_latest_download(download_dir):
    """Rename the most recent downloaded file to teamCSV_DateOfTheDay.csv"""
    files = [os.path.join(download_dir, f) for f in os.listdir(download_dir)]

    if not files:
        print("No downloaded files found")
        return None

    latest_file = max(files, key=os.path.getctime)

    today = datetime.now().strftime("%Y-%m-%d")
    new_filename = f"teamCSV_{today}.csv"
    new_filepath = os.path.join(download_dir, new_filename)

    try:
        if os.path.exists(new_filepath):
            os.remove(new_filepath)
            print(f"Existing file {new_filename} removed, replacing with new data")

        os.rename(latest_file, new_filepath)
        print(f"File renamed to: {new_filename}")
        return new_filepath
    except Exception as e:
        print(f"Error renaming file: {e}")
        return None


def fetch_player_names(sb, output_dir):
    """Extract player names and FIDs from current page"""
    print("Fetching player names...")

    html = sb.get_page_source()
    soup = BeautifulSoup(html, 'html.parser')

    player_data = []
    profile_cells = soup.find_all('div', class_='club-profile-cell-inner')

    for cell in profile_cells:
        try:
            name_span = cell.find('span', class_='club-profile-name')
            fid_span = cell.find('span', class_='club-profile-fid')

            if name_span and fid_span:
                player_info = {
                    'name': name_span.text.strip(),
                    'friend_viewer_id': fid_span.text.strip()
                }
                player_data.append(player_info)
                print(f"Found: {player_info['name']} - FID: {player_info['friend_viewer_id']}")
        except Exception as e:
            print(f"Error extracting player data: {e}")

    if player_data:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        today = datetime.now().strftime("%Y-%m-%d")
        json_filename = f"player_names_{today}.json"
        json_filepath = os.path.join(output_dir, json_filename)

        if os.path.exists(json_filepath):
            print(f"Existing file {json_filename} will be replaced with new data")

        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)

        print(f"\n{len(player_data)} players exported to: {json_filename}")
        return json_filepath
    else:
        print("No players found")
        return None


def calculate_stats(trainer_data):
    """Calculate daily average, weekly average, and monthly total for a trainer"""
    values = [int(v) for v in trainer_data if v and v.strip()]

    if not values:
        return None

    monthly_total = values[-1] if values else 0
    num_days = len(values)

    if num_days == 0:
        return None

    daily_avg = monthly_total / num_days
    weekly_avg = daily_avg * 7

    return {
        "daily_avg": int(daily_avg),
        "weekly_avg": int(weekly_avg),
        "monthly_total": monthly_total
    }


def format_number(num):
    """Format number with thousands separator"""
    return f"{num:,}"


def load_trainer_names(json_file_path):
    """Load trainer ID to name mapping from JSON file"""
    name_mapping = {}
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for trainer in data:
                trainer_id = str(trainer['friend_viewer_id'])
                name = trainer['name']
                name_mapping[trainer_id] = name
    except Exception as e:
        print(f"Warning: Could not load trainer names: {e}")
    return name_mapping


def send_to_discord(webhook_url, csv_file_path, json_file_path):
    """Process CSV and send statistics to Discord webhook"""
    name_mapping = load_trainer_names(json_file_path)
    WEEKLY_REQUIREMENT = 5_000_000

    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)

        all_trainers = []
        meeting_goal = []
        not_meeting_goal = []

        for row in reader:
            if not row or not row[0]:
                continue

            trainer_id = row[0]
            trainer_data = row[1:]

            stats = calculate_stats(trainer_data)

            if stats:
                trainer_name = name_mapping.get(trainer_id, f"Unknown ({trainer_id})")
                meets_goal = stats['weekly_avg'] >= WEEKLY_REQUIREMENT

                trainer_info = {
                    "id": trainer_id,
                    "name": trainer_name,
                    "stats": stats,
                    "meets_goal": meets_goal
                }

                if meets_goal:
                    meeting_goal.append(trainer_info)
                else:
                    not_meeting_goal.append(trainer_info)

        meeting_goal.sort(key=lambda x: x['stats']['weekly_avg'], reverse=True)
        not_meeting_goal.sort(key=lambda x: x['stats']['weekly_avg'], reverse=True)
        all_trainers = meeting_goal + not_meeting_goal

        chunk_size = 24
        embeds = []

        total_trainers = len(all_trainers)
        meeting_count = len(meeting_goal)
        not_meeting_count = len(not_meeting_goal)

        for i in range(0, len(all_trainers), chunk_size):
            chunk = all_trainers[i:i + chunk_size]

            if i == 0:
                description = (
                    f"Statistics as of {datetime.now().strftime('%Y-%m-%d')}\n\n"
                    f"**Weekly Requirement:** {format_number(WEEKLY_REQUIREMENT)}\n"
                    f"**Meeting Goal:** {meeting_count}/{total_trainers}\n"
                    f"**Below Goal:** {not_meeting_count}/{total_trainers}"
                )
                title = "Team Statistics Report"
                color = 3066993
            else:
                description = f"Statistics as of {datetime.now().strftime('%Y-%m-%d')}"
                title = f"Team Statistics (Part {i//chunk_size + 1})"
                color = 5814783

            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": []
            }

            for trainer in chunk:
                status = "✅" if trainer['meets_goal'] else "❌"
                field_value = (
                    f"Daily Avg: {format_number(trainer['stats']['daily_avg'])}\n"
                    f"Weekly Avg: {format_number(trainer['stats']['weekly_avg'])}\n"
                    f"Monthly Total: {format_number(trainer['stats']['monthly_total'])}"
                )

                embed["fields"].append({
                    "name": f"{status} {trainer['name']}",
                    "value": field_value,
                    "inline": True
                })

            embeds.append(embed)

        payload = {"embeds": embeds[:10]}
        response = requests.post(webhook_url, json=payload)

        if response.status_code == 204:
            print("Statistics sent to Discord successfully!")
        else:
            print(f"Failed to send to Discord. Status code: {response.status_code}")
            print(f"Response: {response.text}")


def main(circle_id, download_dir="downloaded_files", webhook_url=None):
    """Main function to download CSV, extract player data, and send to Discord"""
    if not circle_id:
        print("Error: CIRCLE_ID not provided")
        return

    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    with SB(uc=True, headless=True) as sb:
        sb.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": os.path.abspath(download_dir)
        })

        csv_file_path, json_file_path = download_club_csv(sb, circle_id, download_dir)

    if webhook_url and csv_file_path and json_file_path:
        if os.path.exists(csv_file_path) and os.path.exists(json_file_path):
            print("\nSending statistics to Discord...")
            send_to_discord(webhook_url, csv_file_path, json_file_path)
        else:
            print("CSV or JSON files not found, cannot send to Discord")
    elif webhook_url:
        print("Error: CSV or JSON files not generated")


if __name__ == "__main__":
    main(CIRCLE_ID, webhook_url=DISCORD_WEBHOOK_URL)
