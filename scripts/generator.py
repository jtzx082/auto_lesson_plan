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

# ✅ 核心修改：模型优先级列表
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
    # 1. 优先检查环境变量（手动触发）
    if INPUT_TOPIC and INPUT_TOPIC.strip():
        print(f"👉 检测到手动输入课题：{INPUT_TOPIC}")
        return INPUT_TOPIC, False

    # 2. 检查文件是否存在
    if not os.path.exists(TOPIC_FILE):
        print("错误：未找到 topics.txt 文件")
        return None, False
    
    # 3. 读取文件内容
    with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    lines = [line.strip() for line in lines if line.strip()]
    
    if not lines:
        print("任务完成：topics.txt 为空。")
        return None, False
    
    # 4. 提取第一个课题并更新文件
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
    你是一位深刻理解《普通高中化学课程标准》的资深教师。

    # Task
    请严格按照我校规定的《高中化学教学环节》标准，为课题**《{topic}》**设计一份教学设计方案。

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
    * **格式要求**：请使用 **1. 2. 3.** 的序号列表形式，不要使用表格。
    * **内容规范**：参考以下模板进行撰写，将核心素养融入其中，无需单独列出素养名称：
       1. 通过阅读教材/观察实验，了解/理解......（概念/原理）。
       2. 通过......（具体活动），掌握......（重难点），提升......能力。
       3. ......

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
    现在，请开始按照上述五大环节进行设计。重点关注化学式的 Unicode 格式和学习目标的叙述性写法。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    # 针对 Pro 模型增加了 maxOutputTokens，防止生成长教案时中断
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4, 
            "maxOutputTokens": 8192 
        }
    }

    print(f"正在调用 AI 生成优化版教案 (Unicode 格式)...")
    
    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            # 成功情况
            if response.status_code == 200:
                print("成功！✅")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
            # 限流情况 (429) - 进行一次重试
            elif response.status_code == 429:
                print(f"⚠️ 触发限流 (429)。冷却20秒后重试...")
                time.sleep(20)
                print(f"[{model_name}] 重试中...", end=" ")
                retry_resp = requests.post(url, headers=headers, json=data, timeout=120)
                
                if retry_resp.status_code == 200:
                    print("重试成功！✅")
                    return retry_resp.json()['candidates'][0]['content']['parts'][0]['text'], model_name
                else:
                    print(f"重试失败 ({retry_resp.status_code})，切换下一模型。")
            
            # 其他错误 (404, 500 等)
            else:
                print(f"失败 ({response.status_code}) - 正在尝试列表中的下一个模型...")
                
        except Exception as e:
            print(f"异常: {e}")
            # 继续循环尝试下一个模型
            
    return None, None

def main():
    # 检查 API Key
    if not API_KEY:
        print("❌ 错误：未检测到 API Key，请检查 GitHub Secrets 或环境变量设置。")
        sys.exit(1)

    # 获取课题
    topic, is_from_file = get_topic()
    if not topic:
        sys.exit(0)
        
    print(f"📝 当前课题：{topic}")
    
    # 执行生成
    content, used_model = generate_lesson_plan(topic)
    
    if content:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        source_tag = "Manual" if not is_from_file else "Auto"
        
        # 文件名格式：日期_来源_课题.md
        file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# {topic}\n\n")
            f.write(f"> 🤖 模型：{used_model} | 📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"🎉 生成完成！文件位置：{file_name}")
    else:
        print("❌ 生成失败。所有模型均尝试失败，请检查 API 配额或网络连接。")
        sys.exit(1)

if __name__ == "__main__":
    main()
