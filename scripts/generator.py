import os
import sys
import requests
import json
from datetime import datetime

# 1. 基础配置
API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. 候选模型列表 (根据您的诊断日志修改)
# 注意：API 不需要 'models/' 前缀，只需要后面的名字
CANDIDATE_MODELS = [
    "gemini-2.0-flash",       # 【首选】根据日志，您有 2.0 的权限，这比 1.5 强得多！
    "gemini-2.0-flash-exp",   # 2.0 实验版
    "gemini-flash-latest",    # 指向最新 Flash 版本的别名（通常最稳）
    "gemini-2.5-flash",       # 您竟然有 2.5 的权限，如果能跑通将是顶级体验
    "gemini-2.0-flash-lite"   # 极速版作为保底
]

TOPIC_FILE = 'topics.txt'
OUTPUT_DIR = 'generated_plans'

def get_next_topic():
    """读取并移除列表中的第一个课题"""
    if not os.path.exists(TOPIC_FILE):
        print("错误：未找到 topics.txt 文件")
        return None
    
    with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    lines = [line.strip() for line in lines if line.strip()]
    
    if not lines:
        print("任务完成：topics.txt 为空。")
        return None
    
    current_topic = lines[0]
    remaining_topics = lines[1:]
    
    with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(remaining_topics))
        
    return current_topic

def generate_with_retry(topic):
    """尝试使用不同的模型名称生成内容"""
    
    # 针对 Gemini 2.0 优化的提示词
    prompt = f"""
    角色：高中化学高级教师。
    任务：为课题《{topic}》写一份45分钟教案（Markdown格式）。
    
    内容要求：
    1. **【教学目标】** (核心素养维度)
    2. **【教学重难点】**
    3. **【情境引入】** (设计一个生动的生活实例或实验引入)
    4. **【教学过程】** (分步骤设计，包含师生互动环节)
    5. **【板书设计】** (结构图形式)
    6. **【课后作业】**
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7
        }
    }

    # 循环尝试列表中的模型
    for model_name in CANDIDATE_MODELS:
        print(f"尝试模型: {model_name} ...", end=" ")
        
        # 构造 URL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                print("成功！✅")
                result = response.json()
                try:
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return text, model_name
                except Exception:
                    print("解析失败，尝试下一个...")
            else:
                # 打印出失败的状态码，方便调试
                print(f"失败 ({response.status_code})")
                
        except Exception as e:
            print(f"请求异常 ({e})")
            
    return None, None

def main():
    if not API_KEY:
        print("错误：未检测到 GEMINI_API_KEY 环境变量")
        sys.exit(1)

    topic = get_next_topic()
    if not topic:
        sys.exit(0)
        
    print(f"正在为课题【{topic}】寻找可用的 AI 模型...")
    
    content, used_model = generate_with_retry(topic)
    
    if content:
        # 保存结果
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_name = f"{OUTPUT_DIR}/{date_str}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# 课题：{topic}\n\n")
            f.write(f"> 模型：{used_model} | 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"🎉 成功生成教案！文件已保存至：{file_name}")
    else:
        print("\n❌ 所有模型尝试均失败。请检查 API Key 额度或网络。")
        # 恢复 topics.txt
        with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{topic}\n{content}")
        sys.exit(1)

if __name__ == "__main__":
    main()
