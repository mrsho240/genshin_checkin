#!/usr/bin/env python3

import os
import sys
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIGN_URL = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
INFO_URL = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
ACT_ID = "e202102251931481"

def get_headers(cookie, user_agent):
    return {
        "Cookie": cookie,
        "User-Agent": user_agent,
        "Referer": "https://act.hoyolab.com/",
        "Origin": "https://act.hoyolab.com/",
        "Accept-Encoding": "gzip, deflate, br"
    }

def check_already_signed(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.get(f"{INFO_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Info response: {data}")
    if data.get("retcode") == 0:
        return data["data"].get("is_sign", False)
    return False

def do_sign(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.post(f"{SIGN_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Sign response: {data}")
    return data

def send_telegram(token, chat_id, message):
    if not token or not chat_id:
        logger.info("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    logger.info(f"Telegram: {res.status_code} {res.text}")

def send_discord(webhook_url, message):
    if not webhook_url:
        logger.info("Discord not configured")
        return
    res = requests.post(webhook_url, json={"content": message}, timeout=10)
    logger.info(f"Discord: {res.status_code}")

def main():
    cookie = os.getenv("GENSHIN_COOKIE")
    user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    discord_webhook = os.getenv("DISCORD_WEBHOOK")

    if not cookie:
        logger.error("GENSHIN_COOKIE is required")
        sys.exit(1)

    try:
        already_signed = check_already_signed(cookie, user_agent)
        
        if already_signed:
            message = "Genshin check-in: Already checked in today"
            logger.info(message)
            send_telegram(telegram_token, telegram_chat_id, message)
            send_discord(discord_webhook, message)
            sys.exit(0)

        result = do_sign(cookie, user_agent)
        retcode = result.get("retcode", -1)
        msg = result.get("message", "Unknown")

        if retcode == 0:
            message = f"Genshin check-in successful\nMessage: {msg}"
            logger.info(message)
            send_telegram(telegram_token, telegram_chat_id, message)
            send_discord(discord_webhook, message)
            sys.exit(0)
        else:
            message = f"Genshin check-in failed\nRetcode: {retcode}\nMessage: {msg}"
            logger.error(message)
            send_telegram(telegram_token, telegram_chat_id, message)
            send_discord(discord_webhook, message)
            sys.exit(1)

    except Exception as e:
        message = f"Genshin check-in error: {str(e)}"
        logger.error(message)
        send_telegram(telegram_token, telegram_chat_id, message)
        send_discord(discord_webhook, message)
        sys.exit(1)

if __name__ == "__main__":
    main()
