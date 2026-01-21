import os
import sys
import requests
import json
from datetime import datetime

# 1. 基础配置
API_KEY = os.environ.get("GEMINI_API_KEY")

# 2. 候选模型列表 (我们将依次尝试这些名字，直到成功)
# 涵盖了新版、旧版、稳定版和开发版
CANDIDATE_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-pro",         # 1.0 版本，保底稳如老狗
    "gemini-1.0-pro"
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

def debug_available_models():
    """当所有尝试都失败时，列出当前 Key 可用的所有模型"""
    print("\n[诊断模式] 正在查询您的 API Key 可用的模型列表...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            print("--- Google 返回的可用模型 ---")
            for model in data.get('models', []):
                # 只显示支持 generateContent 的模型
                if "generateContent" in model.get('supportedGenerationMethods', []):
                    print(f"- {model['name']}")
            print("-----------------------------")
            print("请从上面选择一个名称，替换代码中的模型名。")
        else:
            print(f"无法获取模型列表。HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"诊断请求失败: {e}")

def generate_with_retry(topic):
    """尝试使用不同的模型名称生成内容"""
    
    prompt = f"""
    角色：高中化学高级教师。
    任务：为课题《{topic}》写一份45分钟教案（Markdown格式）。
    包含：教学目标、重难点、引入、过程、板书、作业。
    """
    
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': API_KEY
    }
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7}
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
                # 如果是 404 (模型未找到) 或 400 (参数错误)，就尝试下一个
                # 如果是 429 (超限)，也可以尝试下一个
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
        print("\n❌ 所有模型尝试均失败。")
        # 触发诊断
        debug_available_models()
        # 恢复 topics.txt (把课题塞回去，免得丢了)
        with open(TOPIC_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        with open(TOPIC_FILE, 'w', encoding='utf-8') as f:
            f.write(f"{topic}\n{content}")
        sys.exit(1)

if __name__ == "__main__":
    main()
