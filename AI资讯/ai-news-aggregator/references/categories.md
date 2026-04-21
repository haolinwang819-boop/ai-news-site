# 分类规则

## 四大模块定义

### 🎨 图视频模块 (image_video)

**关键词匹配**（不区分大小写）：
```
midjourney, mj, dall-e, dalle, stable diffusion, sd, 
sora, runway, pika, kling, 可灵, imagen, 
video generation, image generation, text-to-image, 
text-to-video, 图像生成, 视频生成, AI绘画, AI作图
```

**典型来源**：
- Midjourney官方更新
- Runway新功能
- Stability AI发布

---

### 🤖 基础大模型模块 (llm)

**关键词匹配**：
```
gpt, gpt-4, gpt-5, chatgpt, openai,
claude, anthropic,
gemini, bard, google ai,
llama, meta ai,
qwen, 通义千问, 阿里云,
glm, chatglm, 智谱,
deepseek, 深度求索,
mistral, mixtral,
大语言模型, llm, 大模型, foundation model
```

**典型来源**：
- OpenAI产品发布
- Anthropic技术博客
- Google AI更新

---

### 🚀 黑马AI新品模块 (startup)

**识别规则**：
1. 标题/内容包含：`launch`, `发布`, `beta`, `新品`, `startup`, `融资`
2. 来源为非主流大厂（非OpenAI/Google/Meta/Anthropic/Microsoft）
3. 产品首次出现

**典型来源**：
- ProductHunt AI产品
- TechCrunch创业报道
- 小型AI公司产品发布

---

### 🔥 AI热点资讯模块 (hot_news)

**匹配规则**：
所有包含AI/人工智能关键词但不属于以上三类的内容

**关键词**：
```
artificial intelligence, ai, 人工智能,
machine learning, ml, 机器学习,
deep learning, 深度学习,
neural network, 神经网络
```

**典型内容**：
- AI政策法规
- 行业分析报告
- 技术趋势文章
- AI伦理讨论

---

## 优先级排序规则

### P0 - 重磅更新（置顶显示）
- 主流AI公司（OpenAI/Google/Anthropic/Meta）产品重大版本发布
- 关键词：`release`, `launch`, `发布`, `重磅`, `major update`

### P1 - 重要新闻
- 融资金额 > 1亿美元
- 政策/法规变化
- 技术突破（新论文、新能力）
- 关键词：`billion`, `亿`, `regulation`, `breakthrough`

### P2 - 日常资讯
- 功能更新、小版本发布
- 行业动态、市场分析

### P3 - 其他
- 观点文章、教程、科普内容

---

## 去重规则

1. **URL去重**：同一URL只保留首次出现
2. **标题相似度**：标题相似度>80%视为重复，保留优先级高的来源
3. **时间窗口**：只采集过去24小时内的内容
