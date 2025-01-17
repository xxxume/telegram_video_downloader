import os
import asyncio
from datetime import datetime
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TimedOut, NetworkError
import httpx
import time
import json
import math
import humanize  # 需要安装: pip install humanize

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/root/video/bot.log'),  # 添加文件日志
        logging.StreamHandler()  # 保留控制台输出
    ]
)
logger = logging.getLogger(__name__)

# Telegram Bot配置
BOT_TOKEN = '填入机器人的TOKEN'
ADMIN_USER_ID = 填入你的用户ID
BASE_URL = "https://api.telegram.org/bot"  # 可以根据需要修改为其他 API 地址

# 视频保存路径
DOWNLOAD_PATH = '/root/video'
os.makedirs(DOWNLOAD_PATH, exist_ok=True)

# 存储被监控的频道
monitored_channels = set()

# 添加配置文件保存/加载功能
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

# 添加进度条辅助函数
def create_progress_bar(progress):
    """创建进度条"""
    filled = '█' * int(progress * 10)
    empty = '░' * (10 - int(progress * 10))
    return f"{filled}{empty}"

def format_size(size):
    """格式化文件大小"""
    return humanize.naturalsize(size, binary=True)

async def progress_callback(current, total, message, start_time, file_name):
    """更新下载进度"""
    try:
        now = time.time()
        # 每2秒更新一次进度，避免频繁更新
        if now - progress_callback.last_update < 2:
            return
        progress_callback.last_update = now

        progress = current / total
        bar = create_progress_bar(progress)
        percentage = progress * 100
        
        # 计算速度和剩余时间
        elapsed_time = now - start_time
        speed = current / elapsed_time if elapsed_time > 0 else 0
        eta = (total - current) / speed if speed > 0 else 0
        
        # 格式化消息
        text = (
            f"📥 正在下载: {file_name}\n"
            f"进度: {bar} {percentage:.1f}%\n"
            f"大小: {format_size(current)}/{format_size(total)}\n"
            f"速度: {format_size(speed)}/s\n"
            f"预计剩余时间: {int(eta)}秒"
        )
        
        # 更新消息
        await message.edit_text(text)
    except Exception as e:
        logger.error(f"更新进度时出错: {str(e)}")

# 初始化最后更新时间
progress_callback.last_update = 0

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    logger.info(f"Received /start command from user ID: {update.effective_user.id}")
    
    if update.effective_user.id != ADMIN_USER_ID:
        logger.warning(f"Unauthorized access attempt from user {update.effective_user.id}")
        await update.message.reply_text("抱歉，您没有使用此机器人的权限。")
        return
    
    logger.info("Sending welcome message to admin")
    await update.message.reply_text(
        "欢迎使用频道视频下载机器人！\n"
        "/add_channel <频道链接> - 添加要监控的频道\n"
        "/remove_channel <频道链接> - 移除监控的频道\n"
        "/list_channels - 列出所有监控的频道\n"
        "/status - 查看下载状态和统计信息"
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """添加要监控的频道"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("请提供频道用户名，例如: /add_channel @channel_name")
        return
    
    channel = context.args[0].strip('@')
    try:
        # 验证频道
        chat = await context.bot.get_chat(f"@{channel}")
        if chat.type != 'channel':
            await update.message.reply_text("这不是一个频道")
            return
            
        # 检查机器人权限
        member = await chat.get_member(context.bot.id)
        if not member.status in ['administrator', 'creator']:
            await update.message.reply_text("请先将机器人添加为频道管理员")
            return
        
        monitored_channels.add(channel)
        save_channels()  # 保存配置
        await update.message.reply_text(f"已成功添加频道: @{channel}\n机器人将自动下载该频道的新视频")
        logger.info(f"Added channel: @{channel}")
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"Failed to add channel {channel}: {error_message}")
        if "Chat not found" in error_message:
            await update.message.reply_text("找不到该频道，请确保:\n1. 频道用户名正确\n2. 频道是公开的\n3. 机器人已加入该频道")
        else:
            await update.message.reply_text(f"添加频道失败: {error_message}\n请确保:\n1. 频道用户名正确\n2. 机器人是频道管理员")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """移除监控的频道"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    if not context.args:
        await update.message.reply_text("请提供要移除的频道链接或用户名")
        return
    
    channel = context.args[0]
    if channel.strip('@') in monitored_channels:
        monitored_channels.remove(channel.strip('@'))
        await update.message.reply_text(f"已移除频道: {channel}")
    else:
        await update.message.reply_text("未找到该频道")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """列出所有监控的频道"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    if not monitored_channels:
        await update.message.reply_text("当前没有监控任何频道")
        return
    
    channels_list = "\n".join(f"- {channel}" for channel in monitored_channels)
    await update.message.reply_text(f"当前监控的频道：\n{channels_list}")

async def handle_new_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理新消息，下载视频"""
    logger.info("收到新消息")
    
    if not update.channel_post:
        logger.info("不是频道消息，忽略")
        return
    
    channel_username = update.effective_chat.username
    logger.info(f"消息来自频道: {channel_username}")
    
    if channel_username not in monitored_channels:
        logger.info(f"频道 {channel_username} 不在监控列表中")
        return
    
    try:
        if update.channel_post.video:
            video = update.channel_post.video
            logger.info(f"检测到视频: {video.file_name}, 大小: {format_size(video.file_size)}")
            
            # 修改文件大小限制检查
            if video.file_size > 50 * 1024 * 1024:  # 50MB
                error_msg = (
                    f"文件太大 ({format_size(video.file_size)})，超过 Telegram Bot API 限制\n"
                    f"建议：\n"
                    f"1. 使用较小的视频文件（<50MB）\n"
                    f"2. 或者将视频分段上传\n"
                    f"3. 或者使用其他下载方式"
                )
                logger.error(error_msg)
                await context.bot.send_message(
                    chat_id=ADMIN_USER_ID,
                    text=f"❌ 下载失败\n"
                         f"频道: @{channel_username}\n"
                         f"文件: {video.file_name}\n"
                         f"大小: {format_size(video.file_size)}\n"
                         f"原因: 文件超过50MB限制"
                )
                return
            
            now = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = video.file_name or f'video_{now}.mp4'
            file_path = os.path.join(DOWNLOAD_PATH, file_name)
            
            # 确保文件名唯一
            base_name, ext = os.path.splitext(file_name)
            counter = 1
            while os.path.exists(file_path):
                file_path = os.path.join(DOWNLOAD_PATH, f'{base_name}_{counter}{ext}')
                counter += 1
            
            # 发送初始下载消息
            progress_message = await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"开始下载视频: {file_name}\n大小: {format_size(video.file_size)}"
            )
            
            try:
                # 记录开始时间
                start_time = time.time()
                
                # 下载视频
                logger.info(f'开始下载视频: {file_path}')
                file = await context.bot.get_file(video.file_id)
                await file.download_to_drive(
                    custom_path=file_path,
                    progress_callback=lambda current, total: asyncio.create_task(
                        progress_callback(
                            current, total, progress_message, 
                            start_time, file_name
                        )
                    )
                )
                
                # 下载完成后的处理
                file_size = os.path.getsize(file_path)
                duration = time.time() - start_time
                average_speed = file_size / duration if duration > 0 else 0
                
                # 发送完成消息
                complete_message = (
                    f"✅ 视频下载完成\n"
                    f"频道: @{channel_username}\n"
                    f"文件: {file_name}\n"
                    f"大小: {format_size(file_size)}\n"
                    f"用时: {int(duration)}秒\n"
                    f"平均速度: {format_size(average_speed)}/s"
                )
                
                await progress_message.edit_text(complete_message)
                logger.info(f'视频下载完成: {file_path} ({format_size(file_size)})')
                
            except Exception as e:
                # 如果下载失败，删除可能的部分下载文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                raise e
                
        else:
            logger.info("消息中没有视频")
            
    except Exception as e:
        error_message = f"下载视频时出错: {str(e)}"
        logger.error(error_message)
        # 通知管理员出错
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"❌ 下载失败\n频道: @{channel_username}\n错误: {str(e)}"
        )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示下载状态和统计信息"""
    if update.effective_user.id != ADMIN_USER_ID:
        return
    
    try:
        # 获取下载目录的统计信息
        total_files = len([f for f in os.listdir(DOWNLOAD_PATH) if os.path.isfile(os.path.join(DOWNLOAD_PATH, f))])
        total_size = sum(os.path.getsize(os.path.join(DOWNLOAD_PATH, f)) for f in os.listdir(DOWNLOAD_PATH) if os.path.isfile(os.path.join(DOWNLOAD_PATH, f)))
        
        status_message = (
            "📊 下载统计信息\n"
            f"监控的频道数: {len(monitored_channels)}\n"
            f"已下载文件数: {total_files}\n"
            f"总存储大小: {total_size / 1024 / 1024:.2f} MB\n"
            f"存储路径: {DOWNLOAD_PATH}"
        )
        await update.message.reply_text(status_message)
    except Exception as e:
        await update.message.reply_text(f"获取状态信息时出错: {str(e)}")

def main():
    """启动机器人"""
    logger.info("Bot starting...")
    load_channels()  # 加载保存的频道配置
    logger.info(f"Admin ID: {ADMIN_USER_ID}")
    logger.info(f"Download path: {DOWNLOAD_PATH}")
    logger.info(f"Monitored channels: {monitored_channels}")
    
    while True:
        try:
            # 每次循环创建新的应用实例
            application = (
                Application.builder()
                .token(BOT_TOKEN)
                .connect_timeout(30.0)
                .read_timeout(30.0)
                .write_timeout(30.0)
                .pool_timeout(30.0)
                .get_updates_read_timeout(30.0)
                .build()
            )
            
            logger.info("Application built successfully")
            
            # 注册命令处理器
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("add_channel", add_channel))
            application.add_handler(CommandHandler("remove_channel", remove_channel))
            application.add_handler(CommandHandler("list_channels", list_channels))
            application.add_handler(CommandHandler("status", status))
            
            # 注册消息处理器
            application.add_handler(MessageHandler(
                filters.ChatType.CHANNEL & (filters.VIDEO | filters.FORWARDED),
                handle_new_message
            ))
            
            logger.info("All handlers registered")
            
            # 启动轮询
            logger.info("Starting polling...")
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                timeout=30,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30,
                pool_timeout=30
            )
            
        except (TimedOut, NetworkError) as e:
            logger.error(f"Network error: {e}")
            logger.info("Waiting 10 seconds before retry...")
            time.sleep(10)
            continue
        except Exception as e:
            logger.error(f"Critical error: {str(e)}", exc_info=True)
            logger.info("Waiting 30 seconds before retry...")
            time.sleep(30)
            continue

if __name__ == '__main__':
    try:
        logger.info("Script started")
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True) 