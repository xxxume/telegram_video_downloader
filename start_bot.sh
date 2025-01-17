#!/bin/bash
cd /root/video
source venv/bin/activate

while true; do
    echo "Starting bot..."
    python telegram_video_downloader.py >> /root/video/logs/bot.out 2>&1
    echo "Bot crashed or stopped, restarting in 10 seconds..."
    sleep 10
done