#!/usr/bin/env python3
"""
Genshin Impact Daily Check-in Automation (Fixed)
ทำงานอัตโนมัติและส่งแจ้งเตือนไปยัง Discord/Telegram
"""

import os
import sys
import requests
import json
from datetime import datetime
from typing import Optional, Dict
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GenshinCheckIn:
    """Genshin Impact Daily Check-in Handler"""
    
    # API Endpoints ตามเซิร์ฟเวอร์
    API_ENDPOINTS = {
        'os_asia': 'https://sg-hk4e-api.hoyoverse.com/event/sol/sign',
        'os_cht': 'https://sg-public-api.hoyoverse.com/event/sol/sign',
        'os_euro': 'https://sg-public-api.hoyoverse.com/event/sol/sign',
        'os_usa': 'https://sg-public-api.hoyoverse.com/event/sol/sign',
    }
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://act.hoyoverse.com/ys/event/signin-sea-v3/index.html',
            'Accept-Language': 'th-TH,th;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'application/json, text/plain, */*',
        }
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK')
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
    def check_in(self, uid: str, server: str, cookie: str) -> Dict:
        """
        ทำการ Check-in
        
        Args:
            uid: Game UID ของคุณ (เช่น 123456789)
            server: Server (os_asia, os_cht, os_euro, os_usa)
            cookie: Cookie จากเบราว์เซอร์
        
        Returns:
            dict: ผลลัพธ์การ Check-in
        """
        
        # เลือก Endpoint ตามเซิร์ฟ
        base_url = self.API_ENDPOINTS.get(server, self.API_ENDPOINTS['os_asia'])
        
        # First, check status
        check_url = base_url.replace('/sign', '/sign/home')
        
        params = {
            'act_id': 'e202102251931481',
            'lang': 'th-th'
        }
        
        headers = self.headers.copy()
        headers['Cookie'] = cookie
        
        try:
            logger.info(f"ตรวจสอบสถานะ Check-in...")
            logger.info(f"Server: {server}")
            logger.info(f"URL: {check_url}")
            
            # ตรวจสอบสถานะ
            response = requests.get(check_url, params=params, headers=headers, timeout=10)
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Response: {response.text[:200]}")
            
            if response.status_code == 404:
                logger.warning("Endpoint 404 - ลองใช้ Endpoint อื่น")
                # ลองใช้ Endpoint อื่น
                base_url = 'https://sg-public-api.hoyoverse.com/event/sol/sign'
                check_url = base_url.replace('/sign', '/sign/home')
                response = requests.get(check_url, params=params, headers=headers, timeout=10)
            
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"ตรวจสอบสถานะ: {data}")
            
            # Check-in
            logger.info(f"กำลัง Check-in...")
            checkin_data = {
                'act_id': 'e202102251931481',
                'lang': 'th-th'
            }
            
            checkin_response = requests.post(
                base_url, 
                data=checkin_data, 
                headers=headers, 
                timeout=10
            )
            
            logger.info(f"Check-in Status Code: {checkin_response.status_code}")
            logger.info(f"Check-in Response: {checkin_response.text}")
            
            checkin_response.raise_for_status()
            
            result = checkin_response.json()
            logger.info(f"ผลลัพธ์ Check-in: {result}")
            
            # ตรวจสอบ message
            message = result.get('message', 'Check-in สำเร็จ!')
            
            # ถ้า message บอกว่า "already checked in" ก็ถือว่าสำเร็จ
            if 'already' in message.lower() or 'checked in' in message.lower():
                return {
                    'success': True,
                    'message': '✓ Check-in สำเร็จ! (หรือเช็คอินแล้ว)',
                    'data': result.get('data', {})
                }
            
            return {
                'success': True,
                'message': message,
                'data': result.get('data', {})
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Unexpected Error: {str(e)}")
            return {
                'success': False,
                'message': f'Unexpected Error: {str(e)}'
            }
    
    def send_discord_notification(self, message: str, success: bool = True) -> bool:
        """ส่ง Notification ไปยัง Discord"""
        
        if not self.discord_webhook:
            logger.warning("Discord Webhook ไม่ได้ตั้งค่า")
            return False
        
        try:
            color = 0x00ff00 if success else 0xff0000  # Green or Red
            
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
            logger.info("ส่ง Discord notification สำเร็จ")
            return True
            
        except Exception as e:
            logger.error(f"Error ส่ง Discord: {str(e)}")
            return False
    
    def send_telegram_notification(self, message: str) -> bool:
        """ส่ง Notification ไปยัง Telegram"""
        
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram Token หรือ Chat ID ไม่ได้ตั้งค่า")
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
            logger.info("ส่ง Telegram notification สำเร็จ")
            return True
            
        except Exception as e:
            logger.error(f"Error ส่ง Telegram: {str(e)}")
            return False


def main():
    """Main function"""
    
    # ดึงค่าจาก Environment Variables
    genshin_uid = os.getenv('GENSHIN_UID')
    genshin_server = os.getenv('GENSHIN_SERVER', 'os_asia')
    genshin_cookie = os.getenv('GENSHIN_COOKIE')
    
    if not all([genshin_uid, genshin_cookie]):
        logger.error("ต้องตั้งค่า GENSHIN_UID และ GENSHIN_COOKIE!")
        sys.exit(1)
    
    # สร้าง instance
    bot = GenshinCheckIn()
    
    logger.info(f"เริ่มทำ Daily Check-in...")
    logger.info(f"เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+8')}")
    
    # ทำการ Check-in
    result = bot.check_in(genshin_uid, genshin_server, genshin_cookie)
    
    # สร้างข้อความแจ้งเตือน
    if result['success']:
        message = f"<b>Check-in สำเร็จ!</b>\n{result['message']}\n {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    else:
        message = f"<b>Check-in ล้มเหลว</b>\n{result['message']}\n {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    
    logger.info(message)
    
    # ส่งแจ้งเตือน
    bot.send_discord_notification(message, result['success'])
    bot.send_telegram_notification(message)
    
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
