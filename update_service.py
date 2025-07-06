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
    
    def extract_reddit_id(self, reddit_url):
        try:
            if "/comments/" in reddit_url:
                return reddit_url.split("/comments/")[-1].split("/")[0]
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
            error_msg = str(e)
            if "duplicate key value violates unique constraint" in error_msg and "Tweet_ID" in error_msg:
                return False, "Link has been added already"
            return False, f"Database error: {error_msg}"
    
    def add_new_reddit_post(self, ambassador, reddit_url):
        try:
            # Extract Reddit post ID from URL
            post_id = self.extract_reddit_id(reddit_url)
            if not post_id:
                return False, "Invalid Reddit URL format"
            
            existing = self.supabase.table("reddit").select("id").eq("url", reddit_url).execute()
            if existing.data:
                return False, "Reddit URL already exists"
            
            reddit_data = {
                "poster": ambassador,
                "url": reddit_url,
                "submitted_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("reddit").insert(reddit_data).execute()
            return True, f"Reddit post added for {ambassador}" if result.data else (False, "Failed to insert")
                
        except Exception as e:
            error_msg = str(e)
            if "duplicate key value violates unique constraint" in error_msg:
                return False, "Link has been added already"
            return False, f"Database error: {error_msg}"
    
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
    
    def get_reddit_leaderboard(self):
        try:
            result = self.supabase.table("reddit").select("*").not_.is_("Score", "null").execute()
            print(f"🔍 Reddit query result: {result.data}")  # Debug print
            if not result.data:
                return []
            
            ambassador_stats = {}
            for post in result.data:
                name = post["poster"]  # Use correct column name
                print(f"🔍 Processing post: {name} - Score: {post.get('Score', 0)}")  # Debug print
                if name not in ambassador_stats:
                    ambassador_stats[name] = {
                        "name": name,
                        "posts": 0,
                        "total_score": 0,
                        "total_comments": 0
                    }
                
                ambassador_stats[name]["posts"] += 1
                ambassador_stats[name]["total_score"] += post.get("Score", 0)
                ambassador_stats[name]["total_comments"] += post.get("Comments", 0) if post.get("Comments") else 0
            
            leaderboard = list(ambassador_stats.values())
            leaderboard.sort(key=lambda x: x["total_score"], reverse=True)
            print(f"🔍 Final leaderboard: {leaderboard}")  # Debug print
            return leaderboard
        except Exception as e:
            print(f"❌ Reddit leaderboard error: {e}")  # Debug print
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
    
    def normalize_x_url(self, url):
        """Convert various X/Twitter URL formats to standard x.com format"""
        # Replace various X/Twitter domains with x.com
        url = url.replace("twitter.com", "x.com")
        url = url.replace("fixupx.com", "x.com")
        url = url.replace("fxtwitter.com", "x.com")
        return url
    
    def is_x_url(self, url):
        """Check if URL is from X/Twitter (any supported format)"""
        url_lower = url.lower()
        return any(domain in url_lower for domain in ["x.com", "twitter.com", "fixupx.com", "fxtwitter.com"])
    
    def add_content(self, ambassador, content_url):
        """Unified method to add content - detects platform from URL"""
        try:
            # Detect platform from URL
            if self.is_x_url(content_url):
                # Normalize X URL to x.com format
                normalized_url = self.normalize_x_url(content_url)
                print(f"🐦 X content added for {ambassador}")
                return self.add_new_tweet(ambassador, normalized_url)
            elif "reddit.com" in content_url.lower():
                print(f"📱 Reddit content added for {ambassador}")
                return self.add_new_reddit_post(ambassador, content_url)
            else:
                return False, "Unsupported platform. Please use X (Twitter) or Reddit URLs."
        except Exception as e:
            return False, f"Error processing URL: {str(e)}"
    
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
    
    def calculate_daily_impressions(self, force_update=False):
        """Calculate and store daily impression gains"""
        try:
            today = datetime.now().date()
            
            # Get total impressions from all tweets today
            all_tweets = self.supabase.table("ambassadors").select("Impressions").execute()
            current_total = sum([tweet.get("Impressions", 0) for tweet in all_tweets.data]) if all_tweets.data else 0
            
            # Check if today's record already exists
            existing = self.supabase.table("daily_impressions").select("*").eq("date", today.isoformat()).execute()
            
            if existing.data:
                # Update existing record
                record_id = existing.data[0]["id"]
                old_total = existing.data[0]["total_impressions"]
                impressions_gained = current_total - old_total
                
                self.supabase.table("daily_impressions").update({
                    "total_impressions": current_total,
                    "impressions_gained": max(0, impressions_gained)  # Ensure non-negative
                }).eq("id", record_id).execute()
                
                print(f"📊 Updated daily impressions: +{impressions_gained} (Total: {current_total})")
                return True, f"Daily impressions updated: +{impressions_gained}"
            else:
                # Get yesterday's total to calculate gain
                yesterday = today - timedelta(days=1)
                yesterday_record = self.supabase.table("daily_impressions").select("total_impressions").eq("date", yesterday.isoformat()).execute()
                
                if yesterday_record.data:
                    # Normal case: calculate gain from yesterday
                    yesterday_total = yesterday_record.data[0]["total_impressions"]
                    impressions_gained = current_total - yesterday_total
                else:
                    # First run: set gained to 0 (baseline)
                    impressions_gained = 0
                    print("📊 First run detected - setting baseline with 0 gained impressions")
                
                # Insert new record
                self.supabase.table("daily_impressions").insert({
                    "date": today.isoformat(),
                    "total_impressions": current_total,
                    "impressions_gained": max(0, impressions_gained)  # Ensure non-negative
                }).execute()
                
                if yesterday_record.data:
                    print(f"📊 New daily impressions record: +{impressions_gained} (Total: {current_total})")
                    return True, f"Daily impressions recorded: +{impressions_gained}"
                else:
                    print(f"📊 Baseline set: {current_total} total impressions")
                    return True, f"Baseline established: {current_total} total impressions (0 gained today)"
                
        except Exception as e:
            print(f"❌ Error calculating daily impressions: {e}")
            return False, f"Error: {str(e)}"
    
    def get_daily_impressions_for_month(self, year=None, month=None):
        """Get daily impression gains for a specific month"""
        try:
            if not year:
                year = datetime.now().year
            if not month:
                month = datetime.now().month
                
            # Get start and end of month
            start_date = datetime(year, month, 1).date()
            from calendar import monthrange
            last_day = monthrange(year, month)[1]
            end_date = datetime(year, month, last_day).date()
            
            result = self.supabase.table("daily_impressions").select("date, impressions_gained").gte("date", start_date.isoformat()).lte("date", end_date.isoformat()).order("date").execute()
            
            return result.data if result.data else []
        except Exception as e:
            print(f"❌ Error fetching daily impressions: {e}")
            return []
    
    def reset_today_impressions(self):
        """Reset today's record to 0 gained impressions (useful for first run correction)"""
        try:
            today = datetime.now().date()
            
            # Get total impressions from all tweets
            all_tweets = self.supabase.table("ambassadors").select("Impressions").execute()
            current_total = sum([tweet.get("Impressions", 0) for tweet in all_tweets.data]) if all_tweets.data else 0
            
            # Update today's record to 0 gained
            result = self.supabase.table("daily_impressions").update({
                "total_impressions": current_total,
                "impressions_gained": 0
            }).eq("date", today.isoformat()).execute()
            
            if result.data:
                print(f"📊 Reset today's impressions to baseline: {current_total} total, 0 gained")
                return True, f"Today reset to baseline: {current_total} total impressions"
            else:
                return False, "No record found for today"
                
        except Exception as e:
            print(f"❌ Error resetting today's impressions: {e}")
            return False, f"Error: {str(e)}"
    
    def auto_calculate_daily_impressions(self):
        """Auto-calculate daily impressions only if needed (smart logic)"""
        try:
            today = datetime.now().date()
            
            # Check if today's record already exists
            existing = self.supabase.table("daily_impressions").select("*").eq("date", today.isoformat()).execute()
            
            if existing.data:
                # Record exists - check if it needs updating (only update once per hour to avoid spam)
                existing_record = existing.data[0]
                created_at = datetime.fromisoformat(existing_record['created_at'].replace('Z', '+00:00'))
                hours_since_creation = (datetime.now(created_at.tzinfo) - created_at).total_seconds() / 3600
                
                if hours_since_creation >= 1:  # Update if more than 1 hour old
                    return self.calculate_daily_impressions(force_update=True)
                else:
                    return True, "Daily impressions already calculated recently"
            else:
                # No record for today - create one
                return self.calculate_daily_impressions()
                
        except Exception as e:
            print(f"❌ Error in auto-calculation: {e}")
            return False, f"Auto-calculation error: {str(e)}"