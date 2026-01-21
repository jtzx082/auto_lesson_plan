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
# 获取课时数量，默认为 1
INPUT_PERIOD_COUNT = os.environ.get("INPUT_PERIOD_COUNT", "1") 

# 逻辑：优先尝试最强的 3.0 Pro，如果限流或报错，自动降级到 2.5 Pro，最后用 Flash 保底
CANDIDATE_MODELS = [
    "gemini-3-pro-preview",     # 【首选】最新第3代 Pro，逻辑推理与学科知识最强
    "gemini-2.5-pro",           # 【次选】2.5 Pro，非常稳定的高质量模型
    "gemini-2.5-flash",         # 【保底】2.5 Flash，速度快，成功率极高
    "gemini-2.0-flash"          # 【备用】旧版标准 Flash
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
    
    # 解析课时数
    try:
        p_count = int(INPUT_PERIOD_COUNT)
    except:
        p_count = 1

    # ✅ 核心修改：多课时结构指令
    if p_count > 1:
        period_instruction = f"""
    # 🕒 多课时安排指令 (CRITICAL)
    **本课题共需 {p_count} 个课时 完成教学。**
    **请务必为每一个课时单独设计完整的“五大环节”。**
    
    输出结构必须如下所示（请严格执行）：

    # 第1课时：[子课题名称]
    ## 环节一：学习目标 (针对本课时)
    ## 环节二：情景创设 (针对本课时)
    ## 环节三：任务驱动教学 (针对本课时，含2-3个任务)
    ## 环节四：课堂小结
    ## 环节五：课堂检测 (针对本课时)

    ---
    # 第2课时：[子课题名称]
    ## 环节一：学习目标 (针对本课时)
    ... (重复五大环节) ...
    ## 环节五：课堂检测

    **(以此类推，直到完成所有课时)**
    **注意：每课时时长严格限制为 40 分钟，请确保内容量适中。**
        """
    else:
        period_instruction = """
    # 🕒 课时安排：本课题为 **1课时** 教学设计。
    **注意：本节课时长严格限制为 40 分钟。**
        """

    prompt = f"""
    # Role
    你是一位深刻理解《普通高中化学课程标准》的资深教师。

    # Task
    请严格按照我校规定的《高中化学教学环节》标准，为课题**《{topic}》**设计一份教学设计方案。

    {period_instruction}

    # ⚠️ Formatting Rules (排版至关重要)
    1. **化学式必须使用 Unicode 上下标**：为了保证在纯文本中显示准确，请务必使用特殊的Unicode字符来表示数字和电荷。
       - **正确写法**：H₂O, SO₄²⁻, Fe³⁺, NH₄⁺, CO₂, Al³⁺
       - **错误写法**：H2O, SO42-, Fe3+, $SO_4^2-$
       - *提示：请确保上下标清晰，不要使用 LaTeX 代码块。*
    2. **符号规范**：箭头用 "→"，派键写 "π键"。
    3. **结构清晰**：使用 Markdown 的 ## 标题分层。

    # Structure & Requirements (每个课时都必须包含以下五大环节)
    
    ## 环节一：学习目标
    * **数量**：1~4条，实事求是。
    * **规范**：使用数字序号，叙述性句式（“通过...，理解...”）。

    ## 环节二：情景创设
    * **要求**：选择 生活/实验/前沿 情景之一。
    * **目的**：引发认知冲突，明确本课时目标。
    * **时间**：3分钟左右。

    ## 环节三：任务驱动教学 (核心部分)
    * **逻辑**：将本课时知识拆解为 **2-3个子任务**。
    * **闭环要求**：每个任务必须包含：
       1. **[自主学习] OR [合作探究]** (二选一)
       2. **归纳小结**
       3. **评价训练** (1-2道针对性题目)

    ## 环节四：课堂小结
    * **要求**：构建本课时的思维导图结构。

    ## 环节五：课堂检测
    * **要求**：设计3道综合性题目（基础+提升），检测本课时成效。
    * **注意**：题目中的化学式严格使用 Unicode 上下标。

    ---
    现在，请开始设计。如果有多课时，请务必将每个课时分开撰写，确保每个课时都是一个完整的教学闭环。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4, 
            "maxOutputTokens": 8192 
        }
    }

    print(f"正在调用 AI 生成优化版教案 (Unicode | 40分钟 | 全环节闭环)...")
    if p_count > 1:
        print(f"🔥 模式开启：多课时生成 ({p_count} 课时)")

    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                print("成功！✅")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
            # 限流处理
            elif response.status_code == 429:
                print(f"⚠️ 触发限流 (429)。")
                print(f"   ⏳ 正在冷却 60 秒...", end=" ", flush=True)
                time.sleep(60) 
                print(f"\n[{model_name}] 重试中...", end=" ")
                retry_resp = requests.post(url, headers=headers, json=data, timeout=120)
                
                if retry_resp.status_code == 200:
                    print("重试成功！✅")
                    return retry_resp.json()['candidates'][0]['content']['parts'][0]['text'], model_name
                else:
                    print(f"重试失败 ({retry_resp.status_code})，切换下一模型。")
            
            else:
                print(f"失败 ({response.status_code}) - 正在尝试列表中的下一个模型...")
                
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
        
        # 文件名增加课时标记
        p_count_str = os.environ.get("INPUT_PERIOD_COUNT", "1")
        if p_count_str != "1":
            file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}_{p_count_str}课时.md"
        else:
            file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# {topic}\n\n")
            f.write(f"> 🤖 模型：{used_model} | 📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 🕒 课时：{p_count_str} (每课时40min)\n\n")
            f.write(content)
        
        print(f"🎉 生成完成！文件位置：{file_name}")
    else:
        print("❌ 生成失败。所有模型均尝试失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
