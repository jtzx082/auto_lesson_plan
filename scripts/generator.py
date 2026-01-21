import os
import sys
from google import genai # 注意这里是新的导入方式
from datetime import datetime

# 1. 配置 Client
# 新版 SDK 直接初始化 Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

TOPIC_FILE = 'topics.txt'
OUTPUT_DIR = 'generated_plans'

def get_next_topic():
    """读取并移除列表中的第一个课题 (逻辑不变)"""
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
    """使用新版 SDK 调用 Gemini"""
    
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
    
    print(f"Gemini (New SDK) 正在为您生成课题：{topic} ...")
    
    # 新版调用方式：client.models.generate_content
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    
    # 获取文本的方式变更为 .text (如果没有被拦截)
    return response.text

def main():
    topic = get_next_topic()
    if not topic:
        sys.exit(0)
        
    content = generate_lesson_plan(topic)
    
    # 保存结果
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    file_name = f"{OUTPUT_DIR}/{date_str}_{topic}.md"
    
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(f"# 课题：{topic}\n\n")
        f.write(f"> 模型：Gemini 1.5 Flash (New SDK) | 时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(content)
    
    print(f"成功生成教案：{file_name}")

if __name__ == "__main__":
    main()
