#!/usr/bin/env python3
"""
Google Sheets updater for Streamlit Cloud - runs every 10 minutes
Updates sheet with all data from tweets_data.json
"""

import gspread
from google.oauth2.service_account import Credentials
import json
import time
import schedule
from datetime import datetime
import os

SHEET_NAME = "Nolus_Tweet_Data"
TWEETS_DATA_FILE = "tweets_data.json"

def get_sheet():
    """Get Google Sheet connection for Streamlit Cloud"""
    try:
        # Try to get credentials from Streamlit secrets first
        try:
            import streamlit as st
            creds_dict = dict(st.secrets["gspread"])
            print("📡 Using Streamlit secrets for credentials")
        except:
            # Fallback to environment variable (for local testing)
            creds_json = os.getenv('GOOGLE_CREDENTIALS')
            if creds_json:
                creds_dict = json.loads(creds_json)
                print("📡 Using environment variable for credentials")
            else:
                # Fallback to local file (for development)
                try:
                    with open(".streamlit/secrets.toml", 'r') as f:
                        import toml
                        secrets = toml.load(f)
                        creds_dict = secrets["gspread"]
                        print("📡 Using local secrets.toml for credentials")
                except:
                    print("❌ No credentials found - tried secrets, env var, and local file")
                    return None
        
        # Create credentials and authorize
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        print("✅ Connected to Google Sheets successfully")
        return sheet
        
    except Exception as e:
        print(f"❌ Error connecting to sheet: {e}")
        return None

def load_tweets():
    """Load tweets from JSON file"""
    try:
        if os.path.exists(TWEETS_DATA_FILE):
            with open(TWEETS_DATA_FILE, 'r') as f:
                data = json.load(f)
                print(f"📊 Loaded {sum(len(tweets) for tweets in data.values())} tweets from JSON")
                return data
        else:
            print("📄 No tweets data file found")
            return {}
    except Exception as e:
        print(f"❌ Error loading tweets: {e}")
        return {}

def update_sheet():
    """Update the Google Sheet with all tweet data"""
    print(f"🔄 Starting sheet update at {datetime.now().strftime('%H:%M:%S')}")
    
    # Get data
    tweets_data = load_tweets()
    sheet = get_sheet()
    
    if not sheet:
        print("❌ Cannot update sheet - no connection")
        return False
        
    if not tweets_data:
        print("⚠️ No tweets data to update")
        return False
    
    try:
        # Clear sheet and add headers
        sheet.clear()
        headers = ["Ambassador", "Tweet ID", "Tweet URL", "Submitted Date", "Last Updated", 
                   "Final Update", "Impressions", "Likes", "Retweets", "Replies"]
        sheet.append_row(headers)
        
        # Add all tweets
        total_tweets = 0
        for ambassador, tweets in tweets_data.items():
            for tweet in tweets:
                row = [
                    ambassador,
                    tweet.get("tweet_id", ""),
                    tweet.get("tweet_url", ""),
                    tweet.get("submitted_date", ""),
                    tweet.get("last_updated", ""),
                    tweet.get("final_update", False),
                    tweet.get("impressions", 0),
                    tweet.get("likes", 0),
                    tweet.get("retweets", 0),
                    tweet.get("replies", 0)
                ]
                sheet.append_row(row)
                total_tweets += 1
        
        print(f"✅ Updated sheet with {total_tweets} tweets at {datetime.now().strftime('%H:%M:%S')}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")
        return False

def run_updater():
    """Main function to run the updater"""
    print("🚀 Starting Google Sheets auto-updater...")
    print(f"📅 Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run immediately on start
    update_sheet()
    
    # Schedule every 10 minutes
    schedule.every(10).minutes.do(update_sheet)
    
    print("⏰ Scheduled to run every 10 minutes")
    print("📋 Press Ctrl+C to stop (but don't - let it run!)")
    
    # Keep running
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
        except KeyboardInterrupt:
            print("\n👋 Stopped by user")
            break
        except Exception as e:
            print(f"⚠️ Error in main loop: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    run_updater()