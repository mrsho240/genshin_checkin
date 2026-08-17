#!/usr/bin/env python3
"""
Genshin Impact Daily Check-in Automation
"""

import os
import sys
import requests
import json
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GenshinCheckIn:
    """Genshin Impact Daily Check-in Handler"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://act.hoyoverse.com/ys/event/signin-sea-v3/index.html',
            'Accept-Language': 'th-TH,th;q=0.9',
        }
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
    def check_in(self, uid: str, server: str, cookie: str) -> dict:
        """
        Perform daily check-in
        
        Args:
            uid: Game UID
            server: Server (os_asia, os_cht, os_euro, os_usa)
            cookie: Browser cookies
        
        Returns:
            dict: Result of check-in
        """
        
        # Use the public API endpoint that works for all servers
        url = 'https://sg-public-api.hoyoverse.com/event/sol/sign'
        
        params = {
            'act_id': 'e202102251931481'
        }
        
        headers = self.headers.copy()
        headers['Cookie'] = cookie
        
        try:
            logger.info(f"Attempting check-in for UID: {uid}")
            logger.info(f"Server: {server}")
            logger.info(f"URL: {url}")
            
            # Perform check-in
            response = requests.post(
                url,
                params=params,
                headers=headers,
                timeout=10
            )
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response: {response.text}")
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'message': f'HTTP {response.status_code}: {response.text}'
                }
            
            result = response.json()
            
            # Check for errors in response
            if result.get('retcode') != 0:
                msg = result.get('message', 'Unknown error')
                return {
                    'success': False,
                    'message': msg
                }
            
            logger.info(f"Check-in successful: {result}")
            
            return {
                'success': True,
                'message': result.get('message', 'Check-in successful'),
                'data': result.get('data', {})
            }
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def send_discord_notification(self, message: str, success: bool = True) -> bool:
        """Send notification to Discord"""
        
        if not self.discord_webhook:
            logger.warning("Discord webhook not configured")
            return False
        
        try:
            color = 65280 if success else 16711680  # Green or Red
            
            payload = {
                "embeds": [
                    {
                        "title": "Genshin Impact Check-in",
                        "description": message,
                        "color": color,
                        "timestamp": datetime.utcnow().isoformat(),
                        "footer": {"text": "Auto Check-in Bot"}
                    }
                ]
            }
            
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info("Discord notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Discord error: {str(e)}")
            return False
    
    def send_telegram_notification(self, message: str) -> bool:
        """Send notification to Telegram"""
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info("Telegram notification sent")
            return True
            
        except Exception as e:
            logger.error(f"Telegram error: {str(e)}")
            return False


def main():
    """Main function"""
    
    genshin_uid = os.getenv('GENSHIN_UID')
    genshin_server = os.getenv('GENSHIN_SERVER', 'os_asia')
    genshin_cookie = os.getenv('GENSHIN_COOKIE')
    
    if not all([genshin_uid, genshin_cookie]):
        logger.error("GENSHIN_UID and GENSHIN_COOKIE are required!")
        sys.exit(1)
    
    bot = GenshinCheckIn()
    
    logger.info(f"Starting Daily Check-in")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    result = bot.check_in(genshin_uid, genshin_server, genshin_cookie)
    
    if result['success']:
        message = f"Check-in successful!\n{result['message']}\nTime: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    else:
        message = f"Check-in failed\n{result['message']}\nTime: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
    logger.info(message)
    
    bot.send_discord_notification(message, result['success'])
    bot.send_telegram_notification(message)
    
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
