import os
import sys
import requests
import json
from datetime import datetime

# 1. 基础配置
API_KEY = os.environ.get("GEMINI_API_KEY")
# 直接使用官方 REST API 的标准地址，绝对稳定
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

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

def generate_lesson_plan(topic):
    """使用原生 HTTP 请求调用 Gemini"""
    
    prompt = f"""
    角色：你是一位拥有20年经验的高中化学高级教师。
    任务：请为课题《{topic}》设计一份详细的教学设计方案（45分钟课时）。
    
    要求输出格式为 Markdown，包含以下模块：
    1. **【教学目标】** (核心素养维度)
    2. **【教学重难点】**
    3. **【情境引入】** (设计一个生动的生活实例或实验引入)
    4. **【教学过程】** (分步骤设计，包含师生互动环节)
    5. **【板书设计】** (结构图形式)
    6. **【课后作业】**
    """
    
    print(f"正在通过 REST API 请求生成课题：{topic} ...")
    
    # 构造 Gemini 原生 API 需要的 JSON 结构
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY  # 通过 Header 传递 Key，比 URL 更安全
    }
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        
        # 检查 HTTP 状态码
        if response.status_code != 200:
            print(f"HTTP 错误: {response.status_code}")
            print(f"错误详情: {response.text}")
            raise Exception("API 请求失败")
            
        result = response.json()
        
        # 解析返回的 JSON
        # 路径通常是: candidates[0] -> content -> parts[0] -> text
        try:
            return result['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            print("无法解析返回结果，可能被安全拦截。")
            print(f"原始返回: {result}")
            raise Exception("解析失败")

    except Exception as e:
        print(f"发生异常: {e}")
        raise e

def main():
    if not API_KEY:
        print("错误：未检测到 GEMINI_API_KEY 环境变量")
        sys.exit(1)

    topic = get_next_topic()
    if not topic:
        sys.exit(0)
        
    try:
        content = generate_lesson_plan(topic)
        
        # 保存结果
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        file_name = f"{OUTPUT_DIR}/{date_str}_{topic}.md"
        
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"# 课题：{topic}\n\n")
            f.write(f"> 生成方式：REST API (Requests) | 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"成功生成教案：{file_name}")
        
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
