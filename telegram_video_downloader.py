import os
import asyncio
from datetime import datetime
import logging
from telethon import TelegramClient, events
import humanize
import json
import time

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/root/video/logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Telegram Bot配置
BOT_TOKEN = os.getenv('BOT_TOKEN', '7701103060:AAEfjw6DUzRT3XSQwcTRROL2Q1I8Dkv1PKI')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '1824426271'))

# 使用公共测试服务器的 API ID 和 Hash
API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

# 视频保存路径
DOWNLOAD_PATH = '/root/video'
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# session 文件路径
SESSION_PATH = '/root/video/session/bot_session'

# 存储被监控的频道
monitored_channels = set()

# 保存和加载频道配置
def save_channels():
    with open('/root/video/channels.json', 'w') as f:
        json.dump(list(monitored_channels), f)
    logger.info(f"保存频道配置: {monitored_channels}")

def load_channels():
    try:
        with open('/root/video/channels.json', 'r') as f:
            channels = json.load(f)
            monitored_channels.update(channels)
            logger.info(f"加载频道配置: {monitored_channels}")
    except FileNotFoundError:
        logger.info("没有找到频道配置文件")

def format_size(size):
    """格式化文件大小"""
    return humanize.naturalsize(size, binary=True)

async def progress_callback(current, total, message, start_time, file_name):
    """显示下载进度"""
    try:
        now = time.time()
        # 每2秒更新一次进度
        if hasattr(progress_callback, 'last_update'):
            if now - progress_callback.last_update < 2:
                return
        progress_callback.last_update = now

        # 计算进度
        percentage = (current / total) * 100
        speed = current / (now - start_time) if now - start_time > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0

        # 创建进度条
        bar_length = 10
        filled = int(percentage / 100 * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)

        # 更新消息
        await message.edit(
            f"📥 正在下载: {file_name}\n"
            f"进度: {bar} {percentage:.1f}%\n"
            f"大小: {format_size(current)}/{format_size(total)}\n"
            f"速度: {format_size(speed)}/s\n"
            f"预计剩余时间: {int(eta)}秒"
        )
    except Exception as e:
        logger.error(f"更新进度时出错: {str(e)}")

async def main():
    try:
        # 创建客户端
        logger.info("Creating client...")
        client = TelegramClient(SESSION_PATH, API_ID, API_HASH)
        
        logger.info("Starting client with bot token...")
        await client.start(bot_token=BOT_TOKEN)
        
        logger.info("Bot started successfully")
        logger.info(f"Bot username: {(await client.get_me()).username}")
        
        # 加载保存的频道配置
        load_channels()
        
        @client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            if event.sender_id != ADMIN_USER_ID:
                return
            
            await event.respond(
                "欢迎使用频道视频下载机器人！\n"
                "/add_channel <频道链接> - 添加要监控的频道\n"
                "/remove_channel <频道链接> - 移除监控的频道\n"
                "/list_channels - 列出所有监控的频道\n"
                "/status - 查看下载状态和统计信息"
            )

        @client.on(events.NewMessage(pattern='/add_channel'))
        async def add_channel_handler(event):
            if event.sender_id != ADMIN_USER_ID:
                return
            
            try:
                channel = event.text.split(maxsplit=1)[1].strip('@')
                entity = await client.get_entity(channel)
                if not hasattr(entity, 'broadcast'):
                    await event.respond("这不是一个频道")
                    return
                
                monitored_channels.add(channel)
                save_channels()
                await event.respond(f"已成功添加频道: @{channel}")
                logger.info(f"Added channel: @{channel}")
            except Exception as e:
                await event.respond(f"添加频道失败: {str(e)}")
                logger.error(f"Failed to add channel: {str(e)}")

        @client.on(events.NewMessage(pattern='/remove_channel'))
        async def remove_channel_handler(event):
            if event.sender_id != ADMIN_USER_ID:
                return
            
            try:
                channel = event.text.split(maxsplit=1)[1].strip('@')
                if channel in monitored_channels:
                    monitored_channels.remove(channel)
                    save_channels()
                    await event.respond(f"已移除频道: @{channel}")
                else:
                    await event.respond("未找到该频道")
            except Exception as e:
                await event.respond(f"移除频道失败: {str(e)}")

        @client.on(events.NewMessage(pattern='/list_channels'))
        async def list_channels_handler(event):
            if event.sender_id != ADMIN_USER_ID:
                return
            
            if not monitored_channels:
                await event.respond("当前没有监控任何频道")
                return
            
            channels_list = "\n".join(f"- {channel}" for channel in monitored_channels)
            await event.respond(f"当前监控的频道：\n{channels_list}")

        @client.on(events.NewMessage(pattern='/status'))
        async def status_handler(event):
            if event.sender_id != ADMIN_USER_ID:
                return
            
            try:
                total_files = len([f for f in os.listdir(DOWNLOAD_PATH) if os.path.isfile(os.path.join(DOWNLOAD_PATH, f))])
                total_size = sum(os.path.getsize(os.path.join(DOWNLOAD_PATH, f)) for f in os.listdir(DOWNLOAD_PATH) if os.path.isfile(os.path.join(DOWNLOAD_PATH, f)))
                
                await event.respond(
                    "📊 下载统计信息\n"
                    f"监控的频道数: {len(monitored_channels)}\n"
                    f"已下载文件数: {total_files}\n"
                    f"总存储大小: {format_size(total_size)}\n"
                    f"存储路径: {DOWNLOAD_PATH}"
                )
            except Exception as e:
                await event.respond(f"获取状态信息时出错: {str(e)}")

        @client.on(events.NewMessage)
        async def download_handler(event):
            try:
                # 添加更多日志
                logger.info(f"Received message: {event.message.id}")
                
                if not event.is_channel:
                    logger.info("Not a channel message")
                    return
                
                channel_username = (await event.get_chat()).username
                logger.info(f"Message from channel: @{channel_username}")
                
                if channel_username not in monitored_channels:
                    logger.info(f"Channel @{channel_username} not in monitored list")
                    return

                if hasattr(event.message, 'media') and event.message.media:
                    logger.info("Message has media")
                    # 获取视频信息
                    media = event.message.media
                    if hasattr(media, 'document'):
                        # 获取文件信息
                        file_size = media.document.size
                        mime_type = media.document.mime_type
                        
                        # 只处理视频文件
                        if not mime_type or not mime_type.startswith('video/'):
                            return
                        
                        # 获取文件名
                        for attribute in media.document.attributes:
                            if hasattr(attribute, 'file_name') and attribute.file_name:
                                file_name = attribute.file_name
                                break
                        else:
                            file_name = f"video_{int(time.time())}.mp4"
                        
                        file_path = os.path.join(DOWNLOAD_PATH, file_name)
                        
                        # 确保文件名唯一
                        base_name, ext = os.path.splitext(file_name)
                        counter = 1
                        while os.path.exists(file_path):
                            file_path = os.path.join(DOWNLOAD_PATH, f"{base_name}_{counter}{ext}")
                            counter += 1
                        
                        # 发送开始下载消息
                        status_message = await client.send_message(
                            ADMIN_USER_ID,
                            f"开始下载视频: {file_name}\n大小: {format_size(file_size)}"
                        )
                        
                        try:
                            # 记录开始时间
                            start_time = time.time()
                            
                            # 创建进度回调
                            async def progress(current, total):
                                try:
                                    await progress_callback(current, total, status_message, start_time, file_name)
                                except Exception as e:
                                    logger.error(f"Progress callback error: {str(e)}")
                            
                            # 下载视频
                            await client.download_media(
                                message=event.message.media,
                                file=file_path,
                                progress_callback=progress
                            )
                            
                            # 下载完成后的处理
                            actual_size = os.path.getsize(file_path)
                            duration = time.time() - start_time
                            average_speed = actual_size / duration if duration > 0 else 0
                            
                            # 发送完成消息
                            await status_message.edit(
                                f"✅ 视频下载完成\n"
                                f"频道: @{channel_username}\n"
                                f"文件: {file_name}\n"
                                f"大小: {format_size(actual_size)}\n"
                                f"用时: {int(duration)}秒\n"
                                f"平均速度: {format_size(average_speed)}/s"
                            )
                            
                            logger.info(f"视频下载完成: {file_path}")
                            
                        except Exception as e:
                            # 如果下载失败，删除部分下载的文件
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            raise e
                            
            except Exception as e:
                error_msg = f"下载视频时出错: {str(e)}"
                logger.error(error_msg)
                await client.send_message(
                    ADMIN_USER_ID, 
                    f"❌ 下载失败\n"
                    f"频道: @{channel_username}\n"
                    f"错误: {str(e)}"
                )

        try:
            logger.info("Starting bot...")
            await client.run_until_disconnected()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {str(e)}")
            raise

    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        logger.info("Script started")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True) 