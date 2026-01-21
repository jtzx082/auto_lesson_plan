import os
import sys
import requests
import json
from datetime import datetime

# ================= 配置区 =================
API_KEY = os.environ.get("GEMINI_API_KEY")
INPUT_TOPIC = os.environ.get("INPUT_TOPIC") # 获取手动输入
INPUT_MODE = os.environ.get("INPUT_MODE", "HighQuality") # 获取模式

# 模型优先级列表
# 如果用户选了高质量，优先用 Pro 模型；否则优先用 Flash
if INPUT_MODE == "Fast":
    CANDIDATE_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-flash-latest"]
else:
    # 质量优先：Pro 模型逻辑更强，写出的教案更深刻
    CANDIDATE_MODELS = [
        "gemini-1.5-pro",          # 稳定且聪明
        "gemini-1.5-pro-latest",   
        "gemini-2.0-flash-exp",    # 2.0 虽然叫 Flash 但智商很高
        "gemini-1.5-flash"         # 实在不行再兜底
    ]

TOPIC_FILE = 'topics.txt'
OUTPUT_DIR = 'generated_plans'
# =========================================

def get_topic():
    """
    获取课题逻辑：
    1. 如果有手动输入(INPUT_TOPIC)，直接使用，不修改文件。
    2. 如果没有手动输入，从 topics.txt 读取第一行，并消耗掉。
    """
    # 1. 检查手动输入
    if INPUT_TOPIC and INPUT_TOPIC.strip():
        print(f"👉 检测到手动输入课题：{INPUT_TOPIC}")
        return INPUT_TOPIC, False # False 表示不需要更新文件

    # 2. 检查文件输入
    if not os.path.exists(TOPIC_FILE):
        print("错误：未找到 topics.txt 文件")
        return None, False
    
    with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    lines = [line.strip() for line in lines if line.strip()]
    
    if not lines:
        print("任务完成：topics.txt 为空。")
        return None, False
    
    current_topic = lines[0]
    remaining_topics = lines[1:]
    
    # 更新文件（消耗掉第一行）
    with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(remaining_topics))
        
    return current_topic, True # True 表示需要更新文件

def generate_lesson_plan(topic):
    """
    使用深度 Prompt 生成教案
    """
    
    # === 这是一个经过优化的“深思熟虑”Prompt ===
    prompt = f"""
    # Role
    你是一位拥有25年教龄的**特级高中化学教师**，擅长"启发式教学"和"深度学习"设计。你的教学对象是逻辑思维正在发展的高中生。

    # Task
    请为课题**《{topic}》**设计一份深度教学设计方案（45分钟）。

    # Constraints & Style
    1. **拒绝泛泛而谈**：不要只写“提问”，要写出具体的“核心问题链”。
    2. **拒绝堆砌知识**：重点在于如何让学生“构建”概念，而不是灌输。
    3. **格式**：Markdown，结构清晰，使用 Emoji 点缀但不过分。

    # Content Sections
    请严格按照以下结构输出：

    ## 1. 🎯 核心素养目标 (深度解读)
    * **宏观辨识与微观探析**：(具体结合本课内容写)
    * **证据推理与模型认知**：(具体结合本课内容写)

    ## 2. 💡 学习重难点与认知障碍
    * **重点**：核心概念。
    * **难点**：学生最容易卡住的地方在哪里？
    * **易错点预警**：(列出2个具体的学生常见错误概念)

    ## 3. 🧪 教学过程设计 (核心部分 - 35分钟)
    *(请按“环节-教师活动-学生活动-设计意图”的逻辑撰写)*

    ### 环节一：情境导入 (3-5分钟)
    * **真实情境**：(设计一个与生活紧密相关或震撼的实验现象)
    * **核心驱动问题**：(一个能贯穿整节课的问题)

    ### 环节二：概念构建 (15分钟)
    * **探究活动**：(不要直接讲结论，设计一个探究序列)
    * **关键提问**：(写出老师具体的引导话术)

    ### 环节三：深度辨析与应用 (15分钟)
    * **变式训练**：(设计一道有陷阱的典型例题)
    * **规律总结**：(引导学生自己总结出的口诀或模型)

    ## 4. 📝 板书设计
    (请用 Mermaid 流程图代码或结构化文本展示板书逻辑)

    ## 5. 📚 课后分层作业
    * **基础达标**：(巩固题)
    * **高阶拓展**：(开放性问题或查阅资料)

    ---
    现在，请开始你的教学设计。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    # 适当提高 maxOutputTokens 以确保教案完整
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5, # 稍微降低温度，让内容更严谨
            "maxOutputTokens": 8192
        }
    }

    print(f"正在调用 AI 生成内容 (优先尝试 Pro 模型)...")
    
    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120) # Pro 模型较慢，增加超时时间
            
            if response.status_code == 200:
                print("成功！✅")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            else:
                print(f"失败 ({response.status_code})")
                if response.status_code == 429:
                    print("  -> 触发限流，正在切换下一个模型...")
                
        except Exception as e:
            print(f"异常: {e}")
            
    return None, None

def main():
    if not API_KEY:
        print("❌ 错误：未检测到 API Key")
        sys.exit(1)

    # 1. 获取课题
    topic, is_from_file = get_topic()
    if not topic:
        sys.exit(0)
        
    print(f"📝 当前课题：{topic}")
    
    # 2. 生成内容
    content, used_model = generate_lesson_plan(topic)
    
    if content:
        # 3. 保存
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        # 区分文件名，如果是手动输入的，文件名加个 manual 标记
        source_tag = "Manual" if not is_from_file else "Auto"
        file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# {topic}\n\n")
            f.write(f"> 🤖 模型：{used_model} | 📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"🎉 生成完成！文件位置：{file_name}")
    else:
        print("❌ 生成失败，请检查网络或配额。")
        # 如果是从文件读取的且失败了，要把课题还回去吗？
        # 简单起见，如果刚才读取时已经更新了文件，这里就不回退了，
        # 或者你可以手动把 failed_topics.txt 记录下来。
        sys.exit(1)

if __name__ == "__main__":
    main()
