import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

class UpdateService:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        self.supabase = create_client(url, key)
        print("☁️ Streamlit Cloud service initialized")
    
    def extract_tweet_id(self, tweet_url):
        try:
            if "/status/" in tweet_url:
                return tweet_url.split("/status/")[-1].split("?")[0]
            return None
        except:
            return None
    
    def add_new_tweet(self, ambassador, tweet_url):
        try:
            tweet_id = self.extract_tweet_id(tweet_url)
            if not tweet_id:
                return False, "Invalid tweet URL format"
            
            existing = self.supabase.table("ambassadors").select("id").eq("Tweet_URL", tweet_url).execute()
            if existing.data:
                return False, "Tweet URL already exists"
            
            tweet_data = {
                "Ambassador": ambassador,
                "Tweet_ID": tweet_id,
                "Tweet_URL": tweet_url,
                "Submitted_Date": datetime.now().isoformat(),
                "Last_Updated": datetime.now().isoformat(),
                "Final_Update": False,
                "Impressions": 0,
                "Likes": 0,
                "Retweets": 0,
                "Replies": 0
            }
            
            result = self.supabase.table("ambassadors").insert(tweet_data).execute()
            return True, f"Tweet added for {ambassador}" if result.data else (False, "Failed to insert")
                
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def get_leaderboard(self):
        try:
            # Changed from Final_Update = True to date_posted is not NULL
            result = self.supabase.table("ambassadors").select("*").not_.is_("date_posted", "null").execute()
            if not result.data:
                return []
            
            ambassador_stats = {}
            for tweet in result.data:
                name = tweet["Ambassador"]
                if name not in ambassador_stats:
                    ambassador_stats[name] = {
                        "name": name,
                        "tweets": 0,
                        "total_impressions": 0,
                        "total_likes": 0,
                        "total_replies": 0,
                        "total_retweets": 0
                    }
                
                ambassador_stats[name]["tweets"] += 1
                ambassador_stats[name]["total_impressions"] += tweet["Impressions"]
                ambassador_stats[name]["total_likes"] += tweet["Likes"]
                ambassador_stats[name]["total_replies"] += tweet["Replies"]
                ambassador_stats[name]["total_retweets"] += tweet["Retweets"]
            
            leaderboard = list(ambassador_stats.values())
            leaderboard.sort(key=lambda x: x["total_impressions"], reverse=True)
            return leaderboard
        except:
            return []
    
    def get_update_stats(self):
        try:
            all_tweets = self.supabase.table("ambassadors").select("*").execute()
            # Changed from Final_Update = True to date_posted is not NULL
            updated_tweets = self.supabase.table("ambassadors").select("*").not_.is_("date_posted", "null").execute()
            cutoff_date = datetime.now() - timedelta(days=3)
            cutoff_iso = cutoff_date.isoformat()
            # Changed from Final_Update = False to date_posted is NULL
            ready_tweets = self.supabase.table("ambassadors").select("*").is_("date_posted", "null").lt("Submitted_Date", cutoff_iso).execute()
            
            total = len(all_tweets.data) if all_tweets.data else 0
            updated = len(updated_tweets.data) if updated_tweets.data else 0
            ready = len(ready_tweets.data) if ready_tweets.data else 0
            
            return {
                "total_tweets": total,
                "tweets_updated": updated,
                "tweets_ready_for_update": ready,
                "tweets_under_3_days": max(0, total - updated - ready)
            }
        except:
            return {"total_tweets": 0, "tweets_updated": 0, "tweets_ready_for_update": 0, "tweets_under_3_days": 0}
    
    def get_ready_tweets(self):
        try:
            cutoff_date = datetime.now() - timedelta(days=3)
            cutoff_iso = cutoff_date.isoformat()
            # Changed from Final_Update = False to date_posted is NULL
            result = self.supabase.table("ambassadors").select("*").is_("date_posted", "null").lt("Submitted_Date", cutoff_iso).execute()
            ready_tweets = result.data if result.data else []
            
            for tweet in ready_tweets:
                submitted = datetime.fromisoformat(tweet["Submitted_Date"].replace("Z", "+00:00").replace("+00:00", ""))
                age_days = (datetime.now() - submitted).days
                tweet["days_old"] = age_days
            
            return ready_tweets
        except:
            return []