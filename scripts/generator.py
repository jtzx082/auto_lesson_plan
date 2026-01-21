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
    生成教案（包含重试机制）
    """
    
    # === 优化后的 Prompt：增加了“禁止 LaTeX”的指令 ===
    prompt = f"""
    # Role
    你是一位拥有25年教龄的**特级高中化学教师**。

    # Task
    请为课题**《{topic}》**设计一份深度教学设计方案（45分钟）。

    # ⚠️ Formatting Rules (至关重要)
    1. **绝对禁止使用 LaTeX 格式**：请不要使用美元符号($)，不要使用 \\text{{}} 或 \\ce{{}}。
    2. **化学式写法**：请直接使用普通文本。例如：
       - 写 "H2O" 而不是 "$\text{{H}}_2\text{{O}}$"
       - 写 "CO2" 而不是 "$\text{{CO}}_2$"
       - 写 "Fe3+" (表示离子)
    3. **特殊符号**：
       - 派键：写 "π键"
       - 箭头：写 "->" 或 "→"
       - 杂化：写 "sp2杂化" 或 "sp3杂化"
    4. **整体要求**：确保输出的内容在普通的记事本(Notepad)中也能直接阅读，没有任何代码符号。

    # Content Sections
    请严格按照以下结构输出 Markdown：

    ## 1. 🎯 核心素养目标
    * **宏观辨识与微观探析**：(具体结合内容)
    * **证据推理与模型认知**：(具体结合内容)

    ## 2. 💡 学习重难点
    * **重点**：核心概念。
    * **难点**：学生认知障碍点。
    * **易错点预警**：(列出2个具体错误概念)

    ## 3. 🧪 教学过程设计 (核心部分)
    *(按“环节-教师活动-学生活动-设计意图”逻辑撰写)*

    ### 环节一：情境导入 (生活实例/实验)
    ### 环节二：概念构建 (探究序列)
    ### 环节三：深度辨析 (变式训练)

    ## 4. 📝 板书设计 (结构图)

    ## 5. 📚 分层作业
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

    print(f"正在调用 AI 生成内容...")
    
    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=120)
            
            if response.status_code == 200:
                print("成功！✅")
                return response.json()['candidates'][0]['content']['parts'][0]['text'], model_name
            
            elif response.status_code == 429:
                print(f"⚠️ 触发限流 (429)。")
                print("   ⏳ 正在冷却 20 秒后重试...", end=" ", flush=True)
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
        
        print(f"🎉 生成完成！文件位置：{file_name}")
    else:
        print("❌ 所有尝试均失败。")
        sys.exit(1)

if __name__ == "__main__":
    main()
