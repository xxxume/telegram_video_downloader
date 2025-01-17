# Telegram 视频下载机器人

一个用于自动下载 Telegram 频道视频的机器人。支持大文件下载、进度显示和多频道监控。

## 功能特点

- 🎥 自动下载频道中的视频文件
- 📊 实时显示下载进度和速度
- 📁 支持大文件下载
- 📋 多频道监控管理
- 🔄 自动重试和断点续传
- 📈 下载统计和状态查看

  ![](https://image.xxxu.me/rest/zxk2cNK.png)
  ![](https://image.xxxu.me/rest/QcR2cNK.png)

## 安装步骤

### 1.创建/root/video目录

### 2.下载[文件](https://github.com/xxxume/telegram_video_downloader/releases/tag/%E4%B8%80%E4%B8%AA%E5%8F%AF%E4%BB%A5%E4%B8%8B%E8%BD%BD%E9%A2%91%E9%81%93%E8%A7%86%E9%A2%91%E5%88%B0vps%E6%9C%8D%E5%8A%A1%E5%99%A8%E7%9A%84%E6%9C%BA%E5%99%A8%E4%BA%BA)上传到/root/video目录下

### 3.创建虚拟环境

```
python3 -m venv venv
source venv/bin/activate
```

### 4.安装依赖

```
pip install telethon humanize
```

### 5.创建必要的目录：

```
mkdir -p logs session data
```

### 6.设置权限：

```
chmod +x start\_bot.sh
```

## 配置说明

1. 从 @BotFather 获取 Bot Token
2. 从 @userinfobot 获取你的用户 ID
3. 修改 `telegram_video_downloader.py` 中的配置：
   - BOT_TOKEN
   - ADMIN_USER_ID

## 使用方法

启动机器人：screen -S telegram-bot ./start\_bot.sh   #（按 Ctrl+A+D 将程序放入后台运行）

## 机器人命令

- `/start` - 显示帮助信息
- `/add_channel @channel` - 添加要监控的频道
- `/remove_channel @channel` - 移除监控的频道
- `/list_channels` - 列出所有监控的频道
- `/status` - 查看下载统计信息
  ***初次使用需要/add_channel @你的频道用户名    添加监控频道。

## 常用命令

# 查看日志

tail -f logs/bot.log

# 查看 screen 会话

screen -ls

# 重新连接到 screen 会话

screen -r telegram-bot

# 停止机器人

screen -X -S telegram-bot quit

## 注意事项

1. 确保机器人是频道的管理员
2. 定期清理下载目录避免空间不足
3. 检查日志及时发现问题
4. 建议设置自动备份

## 故障排除

1. 如果机器人无响应：
   
   - 检查日志文件
   - 确认网络连接
   - 验证 Bot Token 是否正确
2. 如果下载失败：
   
   - 检查存储空间
   - 确认文件大小限制
   - 查看错误日志
3. 如果需要重置：
   
   - 停止机器人
   - 清理 session 目录
   - 重新启动

## 更新日志

### v1.0.0

- 初始版本发布
- 支持基本的视频下载功能
- 添加进度显示
- 支持大文件下载

## 许可证

MIT License

## 联系方式

如有问题，请通过 GitHub Issues 反馈。

## 免责说明
此机器人仅供学习交流，请勿违法使用此机器人，使用此机器人所产生的所有后果由使用者承担。

## 贡献

欢迎提交 Issue 和 Pull Request！
