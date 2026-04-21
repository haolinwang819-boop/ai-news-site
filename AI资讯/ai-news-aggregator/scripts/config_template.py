"""
AI资讯采集器配置模板
复制此文件为 config.py 并填入实际配置
"""

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",  # SMTP服务器地址
    "smtp_port": 587,                  # SMTP端口（TLS用587，SSL用465）
    "use_tls": True,                   # 是否使用TLS
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",  # Gmail需使用应用专用密码
    "recipient_email": "recipient@example.com"
}

# X平台API配置（可选）
X_API_CONFIG = {
    "enabled": False,  # 是否启用X采集
    "bearer_token": "",  # X API Bearer Token
    "search_queries": [
        "AI news",
        "GPT",
        "Claude AI",
        "Midjourney",
        "Sora"
    ]
}

# RSS源配置
RSS_SOURCES = [
    # AI官网
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "priority": 0},
    {"name": "Anthropic", "url": "https://www.anthropic.com/feed.xml", "priority": 0},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "priority": 0},
    {"name": "DeepMind", "url": "https://deepmind.google/blog/rss.xml", "priority": 0},
    
    # 英文新闻
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "priority": 1},
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "priority": 1},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "priority": 1},
    
    # 中文新闻
    {"name": "机器之心", "url": "https://www.jiqizhixin.com/rss", "priority": 1},
    {"name": "量子位", "url": "https://www.qbitai.com/feed", "priority": 1},
]

# 采集时间范围（小时）
TIME_RANGE_HOURS = 24

# 每个模块最大条目数
MAX_ITEMS_PER_CATEGORY = 10

# 输出设置
OUTPUT_DIR = "output"  # 临时输出目录
