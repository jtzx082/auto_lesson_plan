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

# 模型列表
CANDIDATE_MODELS = [
    "gemini-3-pro-preview",     # 【首选】
    "gemini-2.5-pro",           # 【次选】
    "gemini-2.5-flash",         # 【保底】
    "gemini-2.0-flash"          # 【备用】
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

def generate_single_period(topic, current_p, total_p, model_hint=None):
    """
    生成【单个课时】的内容
    current_p: 当前是第几课时
    total_p: 总课时数
    """
    
    prompt = f"""
    # Role
    你是一位深刻理解《普通高中化学课程标准》的资深教师。

    # Task
    正在为课题**《{topic}》**设计教学方案。
    **当前任务：请仅设计【第 {current_p} 课时】的详细教学内容。**
    (本课题共 {total_p} 课时，这是其中的第 {current_p} 课时)。

    # Structure & Requirements (必须严格包含以下五大环节)
    请输出 Markdown 格式，标题为：# 第{current_p}课时：[请补充本课时的子课题名称]

    ## 环节一：学习目标 (针对本课时)
    * **规范**：使用数字序号，叙述性句式。

    ## 环节二：情景创设 (针对本课时)
    * **要求**：选择 生活/实验/前沿 情景之一，引发认知冲突。
    * **时间**：3分钟左右。

    ## 环节三：任务驱动教学 (本课时的核心)
    * **逻辑**：将本课时知识拆解为 **2-3个子任务**。
    * **闭环要求**：每个任务必须包含：
       1. **[自主学习] OR [合作探究]** (二选一)
       2. **归纳小结**
       3. **评价训练** (1-2道针对性题目)

    ## 环节四：课堂小结
    * **要求**：构建本课时的思维导图结构。

    ## 环节五：课堂检测
    * **要求**：设计3道综合性题目（基础+提升），检测本课时成效。

    # ⚠️ Formatting Rules
    1. **化学式必须使用 Unicode 上下标** (如 H₂O, Fe³⁺, SO₄²⁻)。
    2. **不要使用 LaTeX**。
    3. **内容要充实**：因为是单课时设计，请确保细节丰富，不仅是框架。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.5, 
            "maxOutputTokens": 8192 
        }
    }

    print(f"   ⏳ 正在生成第 {current_p}/{total_p} 课时...", end=" ")
    
    # 如果有指定的首选模型（比如上一轮成功的模型），优先用它
    models_to_try = CANDIDATE_MODELS
    if model_hint and model_hint in CANDIDATE_MODELS:
        # 将成功过的模型提到最前面
        models_to_try = [model_hint] + [m for m in CANDIDATE_MODELS if m != model_hint]

    for model_name in models_to_try:
        # print(f"[{model_name}]...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                print(f"✅ ({model_name})")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
            elif response.status_code == 429:
                print(f"⚠️ 429限流，冷却20秒...", end=" ")
                time.sleep(20)
                retry_resp = requests.post(url, headers=headers, json=data, timeout=120)
                if retry_resp.status_code == 200:
                    print(f"✅ 重试成功")
                    return retry_resp.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
        except Exception as e:
            print(f"Err: {e}", end=" ")
            
    return None, None

def main():
    if not API_KEY:
        print("❌ 错误：未检测到 API Key")
        sys.exit(1)

    topic, is_from_file = get_topic()
    if not topic:
        sys.exit(0)
        
    # 解析课时数
    try:
        p_count = int(INPUT_PERIOD_COUNT)
    except:
        p_count = 1

    print(f"📝 当前课题：{topic} | 🕒 计划生成：{p_count} 课时")
    
    full_content = ""
    last_used_model = None
    
    # ================= 循环生成所有课时 =================
    for i in range(1, p_count + 1):
        print(f"\n--- 开始处理第 {i} 课时 ---")
        
        # 为了防止连续请求触发 429，每课时间隔一小会儿
        if i > 1:
            print("☕ 休息 10 秒以避免限流...")
            time.sleep(10)

        period_content, used_model = generate_single_period(topic, i, p_count, last_used_model)
        
        if period_content:
            full_content += period_content + "\n\n---\n\n"
            last_used_model = used_model # 记录这次成功的模型，下次优先用
        else:
            print(f"❌ 第 {i} 课时生成失败，流程终止。")
            # 如果中间失败，保存已生成的部分
            full_content += f"\n\n> ⚠️ 错误：第 {i} 课时生成失败，后续中断。\n"
            break
    # ===================================================

    if full_content.strip():
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        source_tag = "Manual" if not is_from_file else "Auto"
        
        if p_count > 1:
            file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}_{p_count}课时.md"
        else:
            file_name = f"{OUTPUT_DIR}/{date_str}_{source_tag}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# {topic} (教学设计)\n\n")
            f.write(f"> 📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 🕒 总课时：{p_count}\n\n")
            f.write(full_content)
        
        print(f"\n🎉 全部完成！文件位置：{file_name}")
    else:
        print("❌ 生成失败，未获得任何内容。")
        sys.exit(1)

if __name__ == "__main__":
    main()
