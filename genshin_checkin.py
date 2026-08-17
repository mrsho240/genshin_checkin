#!/usr/bin/env python3

import os
import sys
import requests
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIGN_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
INFO_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
REWARD_URL  = "https://sg-hk4e-api.hoyolab.com/event/sol/home"
ACT_ID      = "e202102251931481"
UTC8        = timezone(timedelta(hours=8))


def get_headers(cookie, user_agent):
    safe_cookie = cookie.encode("utf-8").decode("latin-1", errors="ignore")
    return {
        "Cookie": safe_cookie,
        "User-Agent": user_agent,
        "Referer": "https://act.hoyolab.com/",
        "Origin": "https://act.hoyolab.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "application/json, text/plain, */*",
    }


def get_sign_info(cookie, user_agent):
    """ดึงข้อมูล check-in status ของเดือนนี้"""
    headers = get_headers(cookie, user_agent)
    res = requests.get(f"{INFO_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Info response: {data}")
    if data.get("retcode") == 0:
        return data["data"]
    return None


def get_reward_list(cookie, user_agent):
    """ดึงรายการรางวัลทั้งเดือน"""
    headers = get_headers(cookie, user_agent)
    res = requests.get(f"{REWARD_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Reward list response retcode: {data.get('retcode')}")
    if data.get("retcode") == 0:
        return data["data"].get("awards", [])
    return []


def do_sign(cookie, user_agent):
    """ทำ check-in"""
    headers = get_headers(cookie, user_agent)
    res = requests.post(f"{SIGN_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Sign response: {data}")
    return data


def is_cookie_expiring_soon():
    """ตรวจสอบว่าวันนี้ใกล้วันที่ 25 ของเดือนหรือไม่"""
    now = datetime.now(UTC8)
    return now.day >= 25


def summarize_monthly_rewards(rewards, total_sign_days):
    """สรุปรางวัลที่ได้รับทั้งเดือนจนถึงวันนี้"""
    summary = {}
    for reward in rewards[:total_sign_days]:
        name = reward.get("name", "Unknown")
        cnt  = reward.get("cnt", 0)
        summary[name] = summary.get(name, 0) + cnt
    return summary


def build_report(sign_info, rewards, today_reward, tomorrow_reward, already_signed):
    """สร้างข้อความ report สำหรับ Telegram"""
    now  = datetime.now(UTC8)
    tmrw = now + timedelta(days=1)

    total_sign_days = sign_info.get("total_sign_day", 0)
    missed_days     = sign_info.get("sign_cnt_missed", 0)

    lines = []
    lines.append("Genshin Impact - Daily Check-in Report")
    lines.append(f"Date: {now.strftime('%d/%m/%Y %H:%M')} (UTC+8)")
    lines.append("")

    # สถานะวันนี้
    if already_signed:
        lines.append("Status: Already checked in today")
    else:
        lines.append("Status: Check-in successful")

    # รางวัลวันนี้
    if today_reward:
        lines.append("")
        lines.append("Today's reward:")
        lines.append(f"  {today_reward.get('name', '-')} x{today_reward.get('cnt', 0)}")

    # รางวัลพรุ่งนี้
    if tomorrow_reward:
        lines.append("")
        lines.append("Tomorrow's reward (preview):")
        lines.append(f"  {tomorrow_reward.get('name', '-')} x{tomorrow_reward.get('cnt', 0)}")

    # สถิติเดือนนี้
    lines.append("")
    lines.append("This month:")
    lines.append(f"  Checked in : {total_sign_days} day(s)")
    lines.append(f"  Missed     : {missed_days} day(s)")

    # สรุปรางวัลทั้งเดือน
    if rewards and total_sign_days > 0:
        monthly = summarize_monthly_rewards(rewards, total_sign_days)
        if monthly:
            lines.append("")
            lines.append("Monthly rewards so far:")
            for item_name, qty in monthly.items():
                lines.append(f"  {item_name} x{qty}")

    # เช็คอินครั้งถัดไป
    lines.append("")
    lines.append("Next check-in:")
    lines.append(f"  {tmrw.strftime('%d/%m/%Y')} at 07:00 (UTC+8)")

    # แจ้งเตือน Cookie ใกล้หมดอายุ
    if is_cookie_expiring_soon():
        lines.append("")
        lines.append("Warning: Cookie may expire soon.")
        lines.append("Please update GENSHIN_COOKIE in GitHub Secrets.")

    return "\n".join(lines)


def send_telegram(token, chat_id, message):
    if not token or not chat_id:
        logger.info("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    logger.info(f"Telegram: {res.status_code}")


def send_discord(webhook_url, message):
    if not webhook_url:
        logger.info("Discord not configured")
        return
    res = requests.post(webhook_url, json={"content": message}, timeout=10)
    logger.info(f"Discord: {res.status_code}")


def main():
    cookie         = os.getenv("GENSHIN_COOKIE")
    user_agent     = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    telegram_chat  = os.getenv("TELEGRAM_CHAT_ID")
    discord_hook   = os.getenv("DISCORD_WEBHOOK")

    if not cookie:
        logger.error("GENSHIN_COOKIE is required")
        sys.exit(1)

    try:
        # ดึงข้อมูล
        sign_info = get_sign_info(cookie, user_agent)
        if not sign_info:
            raise Exception("Failed to get sign info")

        already_signed  = sign_info.get("is_sign", False)
        total_sign_days = sign_info.get("total_sign_day", 0)

        # ดึงรายการรางวัล
        rewards = get_reward_list(cookie, user_agent)

        # รางวัลวันนี้และพรุ่งนี้
        today_idx    = total_sign_days - 1 if already_signed else total_sign_days
        tmrw_idx     = today_idx + 1

        today_reward    = rewards[today_idx]    if rewards and 0 <= today_idx < len(rewards)    else None
        tomorrow_reward = rewards[tmrw_idx]     if rewards and 0 <= tmrw_idx < len(rewards)     else None

        # Check-in ถ้ายังไม่ได้ทำ
        if not already_signed:
            result = do_sign(cookie, user_agent)
            if result.get("retcode") != 0:
                raise Exception(f"Check-in failed: {result.get('message', 'Unknown error')}")

        # สร้าง report
        report = build_report(sign_info, rewards, today_reward, tomorrow_reward, already_signed)

        logger.info(f"\n{report}")
        send_telegram(telegram_token, telegram_chat, report)
        send_discord(discord_hook, report)

        sys.exit(0)

    except Exception as e:
        message = f"Genshin check-in error: {str(e)}"
        logger.error(message)
        send_telegram(telegram_token, telegram_chat, message)
        send_discord(discord_hook, message)
        sys.exit(1)


if __name__ == "__main__":
    main()