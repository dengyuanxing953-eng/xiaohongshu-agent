"""
小红书智能体 Demo
- 接口：novaiapi 中转（OpenAI 兼容）
- 文案：gemini-3-pro-preview
- 生图：gemini-3-pro-image-preview（多模态，base64 出图）
- 界面：Gradio，输出为小红书风格可视化卡片

模型背后是同一个接口，将来换 Claude / ChatGPT 只需改 TEXT_MODEL / IMAGE_MODEL 字符串。
"""

import base64
import html
import io
import json
import os
import re

import gradio as gr
from openai import OpenAI
from PIL import Image

# ---------- 配置（可被环境变量覆盖）----------
BASE_URL = os.getenv("NOVA_BASE_URL", "https://us.novaiapi.com/v1")
API_KEY = os.getenv("NOVA_API_KEY", "")
TEXT_MODEL = os.getenv("TEXT_MODEL", "gemini-3-pro-preview")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview")

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ---------- 风格 ----------
STYLES = {
    "种草": "安利向：突出好物的优点和使用场景，激发购买欲，语气热情真诚。",
    "测评": "测评向：客观对比，列出优点和缺点，给出适合人群，显得专业可信。",
    "教程": "教程向：步骤清晰，干货满满，分点讲解，让人想收藏。",
    "攻略": "攻略向：实用清单/行程，信息密集，省钱省心，方便照着做。",
    "情绪向": "情绪向：有故事感和共鸣，治愈或吐槽，引发情感共振和评论。",
}


# ---------- 文案 ----------
def build_system_prompt(style: str) -> str:
    style_hint = STYLES.get(style, "")
    return f"""你是一个资深的小红书爆款笔记写手，深谙平台调性。

本次笔记风格：{style}。{style_hint}

根据用户给的主题，写一篇有"网感"的小红书笔记。要求：
- 标题：20字以内，带 1-3 个 emoji，制造好奇或痛点，能勾人点进来
- 正文：口语化、真诚、像朋友分享；合理分段，每段配 emoji；结尾引导互动（点赞/收藏/评论）
- 标签：5-8 个精准话题标签，不要带 # 号
- 配图 prompt：用英文写一段适合该笔记的配图描述，符合小红书审美（清新、生活化、高级感）

【严格要求】只输出一个 JSON 对象，不要任何额外文字、不要 markdown 代码块包裹，格式如下：
{{"title": "标题", "body": "正文", "tags": ["标签1", "标签2"], "image_prompt": "english image prompt"}}"""


def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"模型没有返回 JSON：{text[:200]}")
    return json.loads(m.group(0), strict=False)


def generate_copy(topic: str, style: str) -> dict:
    resp = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": build_system_prompt(style)},
            {"role": "user", "content": f"主题：{topic}"},
        ],
        max_tokens=4000,
    )
    raw = resp.choices[0].message.content or ""
    return _extract_json(raw)


# ---------- 生图 ----------
def generate_image_b64(prompt: str) -> str:
    """返回 PNG 的 base64（用于嵌入 HTML 卡片）"""
    resp = client.chat.completions.create(
        model=IMAGE_MODEL,
        messages=[{"role": "user", "content": f"Generate an image: {prompt}"}],
    )
    content = resp.choices[0].message.content or ""
    m = re.search(r"data:image/\w+;base64,([A-Za-z0-9+/=]+)", content)
    if not m:
        raise ValueError(f"返回里没找到图片数据：{content[:200]}")
    img = Image.open(io.BytesIO(base64.b64decode(m.group(1)))).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


# ---------- 卡片渲染 ----------
def render_card(title: str, body: str, tags: list, image_b64: str | None, note: str = "") -> str:
    img_html = (
        f'<img src="data:image/png;base64,{image_b64}" '
        f'style="width:100%;display:block;border-radius:16px 16px 0 0;">'
        if image_b64
        else '<div style="height:180px;display:flex;align-items:center;justify-content:center;'
        'background:#f5f5f5;color:#bbb;border-radius:16px 16px 0 0;">（配图生成失败）</div>'
    )
    tags_html = "".join(
        f'<span style="color:#3a6ea5;font-size:13px;margin-right:6px;">#{html.escape(str(t))}</span>'
        for t in tags
    )
    note_html = (
        f'<div style="color:#e8531a;font-size:12px;margin-top:8px;">{html.escape(note)}</div>'
        if note
        else ""
    )
    return f"""
    <div style="max-width:390px;margin:0 auto;background:#fff;border-radius:16px;
                overflow:hidden;box-shadow:0 6px 24px rgba(0,0,0,0.10);
                font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
      {img_html}
      <div style="padding:16px 18px 20px;">
        <div style="font-size:17px;font-weight:700;color:#222;line-height:1.45;margin-bottom:12px;">
          {html.escape(title)}
        </div>
        <div style="font-size:14px;color:#444;line-height:1.75;white-space:pre-wrap;">
          {html.escape(body)}
        </div>
        <div style="margin-top:14px;">{tags_html}</div>
        {note_html}
      </div>
    </div>
    """


PLACEHOLDER = """
<div style="max-width:390px;margin:0 auto;height:420px;border:2px dashed #ddd;border-radius:16px;
            display:flex;align-items:center;justify-content:center;color:#bbb;
            font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;">
  填入主题，点「生成」，这里会出现笔记卡片
</div>
"""


# ---------- 主流程 ----------
def run(topic: str, style: str):
    if not topic or not topic.strip():
        return render_card("请先输入一个主题", "", [], None)

    try:
        post = generate_copy(topic.strip(), style)
    except Exception as e:
        return render_card("文案生成失败", str(e), [], None)

    title = post.get("title", "")
    body = post.get("body", "")
    tags = post.get("tags", [])
    image_prompt = post.get("image_prompt", title)

    image_b64, note = None, ""
    try:
        image_b64 = generate_image_b64(image_prompt)
    except Exception as e:
        note = f"配图生成失败：{e}"

    return render_card(title, body, tags, image_b64, note)


# ---------- Gradio 界面 ----------
with gr.Blocks(title="小红书智能体") as demo:
    gr.Markdown("# 📕 小红书智能体\n输入主题 → 自动生成笔记文案 + 配图，直接预览成卡片。")

    with gr.Row():
        with gr.Column(scale=2):
            topic_input = gr.Textbox(
                label="主题",
                placeholder="例如：周末露营好物分享 / 平价学生党护肤 / 三亚三天两夜攻略",
            )
            style_input = gr.Radio(
                choices=list(STYLES.keys()),
                value="种草",
                label="风格",
            )
            run_btn = gr.Button("✨ 生成笔记", variant="primary")
            gr.Markdown(
                "<small>背后：文案 gemini-3-pro / 配图 gemini-3-pro-image，"
                "走 novaiapi 中转。换模型只需改环境变量。</small>"
            )
        with gr.Column(scale=3):
            card_out = gr.HTML(value=PLACEHOLDER, elem_classes="card-out")

    run_btn.click(fn=run, inputs=[topic_input, style_input], outputs=card_out)
    topic_input.submit(fn=run, inputs=[topic_input, style_input], outputs=card_out)


if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  未设置 NOVA_API_KEY，请用 run.bat 启动或先设置环境变量。")
    share = os.getenv("GRADIO_SHARE", "0") == "1"
    demo.launch(share=share, css=".card-out{min-height:440px;}")
