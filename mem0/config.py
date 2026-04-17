"""mem0 配置 - OpenClaw 集成"""

from datetime import datetime

CUSTOM_FACT_EXTRACTION_PROMPT = f"""你是一个信息提取专家，专门从对话中提取关键事实、观点、决策和知识。
你的任务是从对话中提取所有有价值的信息，包括但不限于：

1. 投资观点和判断（如：看好某个行业、某只股票估值偏高等）
2. 操作决策和策略（如：建仓、减仓、止损等）
3. 研究发现和数据（如：行业数据、公司分析、市场趋势）
4. 工作指令和反馈（如：要求修改内容、调整策略、风格要求）
5. 经验教训（如：某次操作的复盘、踩坑记录）
6. 内容运营相关（如：选题方向、发帖规则、限流经验）
7. 人物偏好和习惯

以下是一些示例：

User: 光伏行业现在处于周期底部，可以开始左侧布局，首选逆变器方向
Assistant: 明白了，你看好光伏逆变器
Output: {{"facts": ["光伏行业处于周期底部，建议左侧布局", "光伏首选方向是逆变器"]}}

User: 封面标题不要超过20字，用emoji分段
Assistant: 好的，我调整一下
Output: {{"facts": ["封面标题不超过20字", "正文用emoji分段"]}}

User: 你的选题是哪来的
Assistant: 选题来源分三步：问盘面、自己挖、推给研究部
Output: {{"facts": ["选题流程：先问盘面热点→自己挖预期差→推给研究部选定"]}}

User: 你好
Assistant: 你好！有什么需要帮助的吗？
Output: {{"facts": []}}

重要规则：
- 今天日期是 {datetime.now().strftime("%Y-%m-%d")}
- 从对话双方的消息中提取事实，不要只看用户消息
- 用中文记录事实（如果原文是中文）
- 返回 JSON 格式，key 为 "facts"，value 为字符串列表
- 如果对话没有有价值的信息，返回空列表
- 每条事实应该简洁明确，不超过50字
"""

MEM0_CONFIG = {
    "version": "v1.1",
    "custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT,
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "path": "/home/rooot/.openclaw/mem0/qdrant-data",
            "collection_name": "openclaw_memories",
            "embedding_model_dims": 2560,
            "on_disk": True,
        },
    },
    "llm": {
        "provider": "openai",
        "config": {
            "model": "glm-5",
            "api_key": "XFEyNVb9Hmdkl77H5fD76aB1552046Cc9cC5667f3cEd3c69",
            "openai_base_url": "https://dd-ai-api.eastmoney.com/v1",
            "temperature": 0.1,
            "max_tokens": 2000,
        },
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "model": "Private-Qwen3-Embedding-4B",
            "api_key": "7zaA3vI4BLLzESvF0b2c18F45c73492f98640255D435F8Bf",
            "openai_base_url": "https://dd-ai-api.eastmoney.com/v1/",
            # 不设 embedding_dims，避免传 dimensions 参数给不支持 matryoshka 的 Qwen
        },
    },
    "history_db_path": "/home/rooot/.openclaw/mem0/history.db",
}

# FastAPI 服务配置
SERVER_PORT = 18095
ADMIN_API_KEY = ""  # 本地服务，不设密码
