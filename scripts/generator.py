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

# ✅ 稳健模型列表 (确保有 1.5 Flash 保底，防止报错)
CANDIDATE_MODELS = [
    "gemini-2.0-flash",       # 【首选】速度快，智商高，支持中文好
    "gemini-2.0-flash-exp",   # 【备选】
    "gemini-1.5-flash",       # 【强力保底】几乎永不限流，确保您能拿到结果
    "gemini-flash-latest"     
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

    # ✅ 动态构建课时与时间要求提示词
    if p_count > 1:
        period_instruction = f"""
    # 🕒 课时安排特别指令 (重要！)
    **本课题共需 {p_count} 个课时 完成教学。**
    **注意：每课时时长严格限制为 40 分钟。**
    请在设计教案时进行如下结构调整：
    1. **环节一（学习目标）**：制定整体的单元学习目标。
    2. **环节三（任务驱动教学）**：请务必**明确划分课时**。
       - 使用 `### 第1课时：[子主题]`、`### 第2课时：[子主题]` 进行分层。
       - 确保每个课时内都有完整的"学-结-练"闭环，且内容量符合 40 分钟教学节奏。
    3. **环节五（课堂检测）**：请按课时分别设计检测题。
        """
    else:
        period_instruction = "# 🕒 课时安排：本课题为 **1课时** 教学设计。\n    **注意：本节课时长严格限制为 40 分钟，请合理规划各环节时间分配。**"

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

    # Structure & Requirements (严格对应学校标准)
    请按照以下五个环节输出 Markdown 内容：

    ## 环节一：学习目标
    * **数量要求**：请根据本节课知识点的实际深度和广度，**灵活确定目标数量**（通常为1~4条）。不要机械地固定为3条，**实事求是**，既不要凑数也不要遗漏。
    * **格式要求**：使用数字序号列表。
    * **内容规范**：采用叙述性句式，将核心素养自然融入其中。参考模板：
       1. 通过......（具体活动/阅读），了解/理解......（概念/原理）。
       2. 结合......（实验/情境），掌握......（重难点），提升......（学科能力）。

    ## 环节二：情景创设
    * **要求**：选择以下三种情景之一，并说明设计意图：
       1. **生活情境** (如铁生锈、胃药原理)
       2. **实验情境** (趣味实验、视觉冲击)
       3. **前沿情境** (新能源、新材料)
    * **目的**：引发认知冲突，明确本课目标。
    * **时间控制**：导入环节控制在 3-5 分钟以内。

    ## 环节三：任务驱动教学 (核心部分)
    * **逻辑**：将本课核心知识拆解为核心任务 (子任务)。
    * **结构**：如果不仅是一个课时，请按 `### 第X课时` 清晰分隔。
    * **每个任务/课时**必须包含以下三个步骤 (严禁遗漏)：
       1. **自主学习 OR 合作探究** (二选一)：
          - *简单概念* -> 选择 **[自主学习]** (设计学习单问题)。
          - *难点/探究* -> 选择 **[合作探究]** (设计开放性问题)。
       2. **归纳小结**：梳理该任务的知识脉络。
       3. **评价训练**：设计1-2道具体的检测题。

    ## 环节四：课堂小结
    * **要求**：构建本节课的完整知识体系/思维导图结构。

    ## 环节五：课堂检测
    * **要求**：设计3道综合性题目（基础+提升），检测整体学习成效。
    * **注意**：题目中的化学式也必须严格使用 Unicode 上下标 (如 Cl⁻, Na⁺)。

    ---
    现在，请开始按照上述五大环节进行设计。重点关注化学式的 Unicode 格式和 40 分钟的时间分配。
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

    print(f"正在调用 AI 生成优化版教案 (Unicode 格式 | 40分钟标准)...")
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
            
            # 遇到限流，等待 60 秒 (Google 配额重置通常需要一分钟)
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
