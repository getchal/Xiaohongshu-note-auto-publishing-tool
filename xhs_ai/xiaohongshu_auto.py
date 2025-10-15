import os
import requests
import re  # 新增正则表达式模块
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time
import random

# 加载环境变量
load_dotenv()


class XiaohongshuAutoGenerator:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        self.notes_count = int(os.getenv("NOTES_COUNT", 1))
        self.images_per_note = int(os.getenv("IMAGES_PER_NOTE", 3))
        self.content_theme = os.getenv("CONTENT_THEME", "美食推荐")
        self.style = os.getenv("STYLE", "专业")
        self.target_audience = os.getenv("TARGET_AUDIENCE", "20-30岁男性")

        # 确保输出目录存在
        os.makedirs("output/notes", exist_ok=True)
        os.makedirs("output/images", exist_ok=True)

    def call_deepseek_api(self, prompt):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [{
                "role": "user",
                "content": prompt
            }],
            "temperature": 0.7
        }
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            raise Exception(f"API调用失败: {response.status_code}, {response.text}")

    def generate_note_title(self):
        prompt = f"""请为小红书生成一个关于{self.content_theme}的爆款标题，要求：
        1. 包含emoji表情
        2. 严格控制在19字以内（当前字数为：19）
        3. 风格为{self.style}
        4. 目标受众是{self.target_audience}
        请直接返回标题内容，不需要其他说明。"""

        title = self.call_deepseek_api(prompt).strip('"')

        # 双重检查确保不超过20字
        if len(title) > 19:
            title = title[:19]
            print(f"注意：标题超过19字，已截断为：{title}")

        return title

    def generate_note_content(self, title):
        prompt = f"""根据以下标题为小红书生成一篇完整的笔记文案：
        标题：{title}
        要求：
        1. 文案风格为{self.style}
        2. 目标受众是{self.target_audience}
        3. 包含适当的表情符号
        4. 段落分明，有吸引力
        5. 结尾添加3-5个相关话题标签
        请直接返回文案内容，不需要其他说明。"""
        return self.call_deepseek_api(prompt)

    def generate_image_html(self, description):
        prompt = f"""根据以下内容生成一个适合小红书配图的HTML代码：
        描述：{description}
        要求：
        1. 使用div布局，宽度750px，高度任意
        2. 背景色为浅粉色或浅黄色
        3. 包含美观的文字排版
        4. 添加一些装饰元素
        5. 风格为{self.style}
        6. **重要**：请确保只返回纯HTML代码，不要包含任何Markdown标记(如```html)
        请直接返回代码内容，不要任何说明性文字。"""
        return self.call_deepseek_api(prompt)

    def render_html_to_image(self, html, filename):
        # 双重清理：同时去除Markdown代码块标记和HTML注释
        clean_html = re.sub(r'```(html)?|<!--.*?-->', '', html, flags=re.DOTALL)

        # 确保不会泄露任何代码标识
        clean_html = f"""
        <style>
            * {{ 
                font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
                word-break: break-word;
            }}
        </style>
        {clean_html}
        """

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.set_viewport_size({"width": 800, "height": 1200})
            page.set_content(clean_html)
            time.sleep(1.5)  # 增加渲染时间确保完整加载

            # 使用更精准的截图方式
            element = page.query_selector("body > div:first-child")
            element.screenshot(path=filename)

            browser.close()

    def generate_single_note(self, index):
        title = self.generate_note_title()
        print(f"生成笔记 {index + 1}: {title}")

        content = self.generate_note_content(title)
        image_filenames = []

        for i in range(self.images_per_note):
            desc_start = random.randint(0, len(content) // 2)
            desc_end = desc_start + random.randint(50, 150)
            description = content[desc_start:desc_end]

            html = self.generate_image_html(description)
            image_filename = f"output/images/note_{index}_img_{i}.png"
            self.render_html_to_image(html, image_filename)
            image_filenames.append(image_filename)

        note_filename = f"output/notes/note_{index}.txt"
        with open(note_filename, "w", encoding="utf-8") as f:
            f.write(f"标题: {title}\n\n")
            f.write(f"文案:\n{content}\n\n")
            f.write("配图:\n")
            for img in image_filenames:
                f.write(f"{img}\n")

        return note_filename

    def generate_all_notes(self):
        for i in range(self.notes_count):
            try:
                self.generate_single_note(i)
                print(f"成功生成笔记 {i + 1}/{self.notes_count}")
            except Exception as e:
                print(f"生成笔记 {i + 1} 时出错: {str(e)}")


if __name__ == "__main__":
    generator = XiaohongshuAutoGenerator()
    generator.generate_all_notes()
    print("所有笔记生成完成！")