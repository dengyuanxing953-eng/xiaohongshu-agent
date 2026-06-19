# 小红书智能体 Demo

输入主题 → 自动生成小红书笔记文案（Claude）+ 配图（OpenAI gpt-image-1），网页界面（Gradio）。

## 1. 安装依赖

建议用虚拟环境：

```bash
cd xiaohongshu-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 2. 设置两个 API Key

```bash
# macOS / Linux / WSL
export ANTHROPIC_API_KEY="你的Claude密钥"
export OPENAI_API_KEY="你的OpenAI密钥"

# Windows PowerShell
$env:ANTHROPIC_API_KEY="你的Claude密钥"
$env:OPENAI_API_KEY="你的OpenAI密钥"
```

## 3. 运行

```bash
python app.py
```

启动后浏览器打开终端里给出的地址（默认 http://127.0.0.1:7860），
输入主题点「生成」即可。

## 文件说明

- `app.py` — 全部逻辑：Gradio 界面 + Claude 文案 + OpenAI 生图
- `requirements.txt` — 依赖
- `XHSPost` 数据结构 — 标题 / 正文 / 标签 / 配图prompt，由 Claude 结构化输出

## 后续扩展方向

- 文案风格切换（种草 / 测评 / 教程 / 情绪向）
- 一次出多张图供挑选、文案/图「换一版」
- 上云部署 + 接入飞书机器人（核心逻辑不变，替换前端入口即可）
