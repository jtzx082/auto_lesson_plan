import os
import sys
from openai import OpenAI
from datetime import datetime

# 【核心修改】：使用 OpenAI 库调用 Google Gemini
# Google 官方提供的兼容接口地址
client = OpenAI(
    api_key=os.environ.get("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

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
    """使用通用接口生成教案"""
    
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
    
    print(f"Gemini (Universal API) 正在为您生成课题：{topic} ...")
    
    try:
        response = client.chat.completions.create(
            model="gemini-1.5-flash", # 这里直接用模型名
            messages=[
                {"role": "system", "content": "你是一个专业的教育专家。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用出错: {e}")
        # 如果出错，为了防止 topics.txt 里的题目白白被删掉，这里可以抛出异常
        raise e

def main():
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
            f.write(f"> 模型：Gemini 1.5 Flash (Via OpenAI API) | 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write(content)
        
        print(f"成功生成教案：{file_name}")
        
    except Exception as e:
        print("生成失败，请检查 API Key 或网络连接。")
        sys.exit(1)

if __name__ == "__main__":
    main()
