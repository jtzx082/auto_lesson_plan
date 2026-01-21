import os
import sys
import requests
import json
import time
from datetime import datetime

# ================= 配置区 =================
API_KEY = os.environ.get("GEMINI_API_KEY")
INPUT_TOPIC = os.environ.get("INPUT_TOPIC") 
INPUT_MODE = os.environ.get("INPUT_MODE", "HighQuality")

# 优选模型列表 (优先使用高智商模型以理解复杂的任务驱动逻辑)
CANDIDATE_MODELS = [
    "gemini-2.0-flash",       
    "gemini-2.0-flash-exp",   
    "gemini-flash-latest",    
    "gemini-2.0-pro-exp-02-05" 
]

TOPIC_FILE = 'topics.txt'
OUTPUT_DIR = 'generated_plans'
# =========================================

def get_topic():
    """获取课题逻辑"""
    if INPUT_TOPIC and INPUT_TOPIC.strip():
        print(f"👉 检测到手动输入课题：{INPUT_TOPIC}")
        return INPUT_TOPIC, False

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
    
    with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(remaining_topics))
        
    return current_topic, True

def generate_lesson_plan(topic):
    """
    基于《高中化学教学环节》标准生成教案
    """
    
    prompt = f"""
    # Role
    你是一位深刻理解《普通高中化学课程标准》的资深教师。你完全遵循"素养导向、任务驱动"的教学理念。

    # Task
    请严格按照我校规定的《高中化学教学环节》标准，为课题**《{topic}》**设计一份教学设计方案。

    # ⚠️ Formatting Rules (去代码化)
    1. **绝对禁止 LaTeX**：化学式直接写文本（如 H2O, Fe3+, CO2），不要用 $ 符号。
    2. **符号规范**：箭头用 "->" 或 "→"，派键写 "π键"。
    3. **可读性**：输出必须适合直接复制到 Word 文档中。

    # Structure & Requirements (严格对应学校标准)
    请按照以下五个环节输出 Markdown 内容：

    ## 环节一：学习目标
    * **要求**：深度融合高中化学五大核心素养（宏观辨识与微观探析、变化观念与平衡思想、证据推理与模型认知、科学探究与创新意识、科学态度与社会责任）。
    * **表述**：目标清晰可量化（使用“能写出”、“会分析”、“能设计”等动词）。

    ## 环节二：情景创设
    * **要求**：选择以下三种情景之一，并说明设计意图：
        1. **生活情境** (如铁生锈、胃药原理)
        2. **实验情境** (趣味实验、视觉冲击)
        3. **前沿情境** (新能源、新材料)
    * **目的**：引发认知冲突，明确本课目标。

    ## 环节三：任务驱动教学 (核心部分)
    * **逻辑**：将本课核心知识拆解为 **2-3个核心任务 (子任务)**。
    * **每个任务**必须包含以下三个步骤 (严禁遗漏)：
        1. **自主学习 OR 合作探究** (二选一)：
           - *简单概念/性质* -> 选择 **[自主学习]** (设计学习单问题，引导研读教材)。
           - *难点/原理/实验* -> 选择 **[合作探究]** (设计开放性问题，组织小组讨论)。
        2. **归纳小结**：梳理该任务的知识脉络、重点和易错点。
        3. **评价训练**：针对该任务设计1-2道具体的检测题 (基础题或提升题)。

    ## 环节四：课堂小结
    * **要求**：构建本节课的完整知识体系/思维导图结构。

    ## 环节五：课堂检测
    * **要求**：设计3道综合性题目（兼顾基础达标与能力提升），检测整体学习成效。

    ---
    现在，请开始按照上述五大环节进行设计。确保"环节三"中的每个任务都形成了"学-结-练"的闭环。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4, # 稍微降低温度，确保严格遵守结构
            "maxOutputTokens": 8192
        }
    }

    print(f"正在调用 AI 生成符合新课标的教案...")
    
    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                print("成功！✅")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
            elif response.status_code == 429:
                print(f"⚠️ 触发限流 (429)。冷却20秒...")
                time.sleep(20)
                print("重试中...", end=" ")
                retry_resp = requests.post(url, headers=headers, json=data, timeout=120)
                if retry_resp.status_code == 200:
                    print("重试成功！✅")
                    return retry_resp.json()['candidates'][0]['content']['parts'][0]['text'], model_name
                else:
                    print(f"重试失败 ({retry_resp.status_code})")
            else:
                print(f"失败 ({response.status_code})")
                
        except Exception as e:
            print(f"异常: {e}")
            
    return None, None

def main():
    if not API_KEY:
        print("❌ 错误：未检测到 API Key")
        sys.exit(1)

    topic, is_from_file = get_topic()
    if not topic:
        sys.exit(0)
        
    print(f"📝 当前课题：{topic}")
    
    content, used_model = generate_lesson_plan(topic)
    
    if content:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        source_tag = "Manual" if not is_from_file else "Auto"
        file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# {topic}\n\n")
            f.write(f"> 🤖 模型：{used_model} | 📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"🎉 生成完成！教案已严格对标学校标准。位置：{file_name}")
    else:
        print("❌ 生成失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
