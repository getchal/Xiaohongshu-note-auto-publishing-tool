import os
import time
import re
from playwright.sync_api import sync_playwright

def read_note_and_images(note_index):
    note_path = f"output/notes/note_{note_index}.txt"
    images_dir = "output/images"
    # 读取标题和正文
    with open(note_path, "r", encoding="utf-8") as f:
        content = f.read()
    title_match = re.search(r"标题:\s*(.*)", content)
    title = title_match.group(1).strip() if title_match else ""
    content_match = re.search(r"文案:\s*([\s\S]*?)配图:", content)
    note_content = content_match.group(1).strip() if content_match else ""
    # 自动匹配图片
    images = []
    i = 0
    while True:
        img_path = os.path.join(images_dir, f"note_{note_index}_img_{i}.png")
        if os.path.exists(img_path):
            images.append(img_path)
            i += 1
        else:
            break
    return title, note_content, images

def test_publish(note_index=0):
    screenshot_dir = "output/screenshots"
    os.makedirs(screenshot_dir, exist_ok=True)
    title, note_content, images = read_note_and_images(note_index)
    print(f"标题: {title}")
    print(f"正文: {note_content[:30]}...")
    print(f"图片: {images}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state="redbook_auth_state.json" if os.path.exists("redbook_auth_state.json") else None,
            viewport={"width": 1200, "height": 800}
        )
        page = context.new_page()
        try:
            page.goto("https://creator.xiaohongshu.com/publish/publish?source=official&from=tab_switch")

            # 等待核心容器加载
            page.wait_for_selector(".creator-container", state="visible", timeout=20000)

            # 精准定位上传图文组件
            try:
                # 主定位策略：通过层级结构和类名精准定位
                tab = page.locator(".creator-container .header .creator-tab:has(.title:text('上传图文'))")

                # 备选策略1：通过活动状态定位
                if not tab.is_visible(timeout=3000):
                    tab = page.locator(".creator-tab--active .title:text('上传图文')")

                # 备选策略2：通过容器结构定位
                if not tab.is_visible(timeout=3000):
                    tab = page.locator(".upload-container .creator-tab:has(.title:text('上传图文'))")

                # 确保元素可交互
                tab.scroll_into_view_if_needed()
                tab.wait_for(state="visible", timeout=8000)

                if tab.is_enabled():
                    # 高亮显示便于调试
                    tab.evaluate("element => element.style.outline = '3px solid #ff0000'")

                    # 安全点击（添加延时模拟人工操作）
                    tab.click(delay=150)
                    print("已点击上传图文标签")

                    # 验证切换成功
                    try:
                        # 等待图片上传区域出现
                        page.wait_for_selector("text=拖拽图片到此或点击上传", timeout=8000)
                    except:
                        # 检查标签激活状态
                        if "creator-tab--active" in tab.get_attribute("class"):
                            print("类名验证切换成功")
                        else:
                            # 检查下划线指示器位置
                            underline = page.locator(".underline")
                            if underline.is_visible():
                                tab_rect = tab.bounding_box()
                                underline_rect = underline.bounding_box()
                                if abs(tab_rect['x'] - underline_rect['x']) < 10:
                                    print("下划线位置验证切换成功")

                    print("成功切换到上传图文界面")
                else:
                    page.screenshot(path=f"{screenshot_dir}/tab_disabled_{int(time.time())}.png")
                    print("上传图文标签不可点击，已截图")

            except Exception as e:
                page.screenshot(path=f"{screenshot_dir}/tab_error_{int(time.time())}.png")
                print(f'切换标签失败: {e}')
                # JavaScript终极解决方案
                page.evaluate("""() => {
                    const tabs = document.querySelectorAll('.creator-tab');
                    for (const tab of tabs) {
                        const title = tab.querySelector('.title');
                        if (title && title.textContent.includes('上传图文')) {
                            tab.style.outline = '3px solid red';
                            tab.click();
                            return true;
                        }
                    }
                    return false;
                }""")
                print("已执行JavaScript强制切换操作")

            # 上传图片（逐张上传）
            try:
                file_input = page.locator("input[type='file']").first
                if file_input.is_visible():
                    for img in images:
                        file_input.set_input_files(img)
                        time.sleep(3)  # 等待图片上传完成，可根据实际情况调整
                else:
                    page.screenshot(path=f"{screenshot_dir}/upload_file_input_error_{int(time.time())}.png")
                    print("未找到图片上传输入框，已截图")
            except Exception as e:
                page.screenshot(path=f"{screenshot_dir}/upload_crash_{int(time.time())}.png")
                print(f'上传图片时浏览器崩溃，已截图: {e}')

            # 检查是否有“下一步”按钮
            next_btn = page.locator("button:has-text('下一步'), button:has-text('继续')").first
            if next_btn.is_visible():
                next_btn.click()
                time.sleep(2)

            # 等待标题输入框出现
            try:
                page.wait_for_selector("input[placeholder*='标题'], input[placeholder*='填写标题']", timeout=15000)
            except Exception:
                page.screenshot(path=f"{screenshot_dir}/title_input_wait_timeout_{int(time.time())}.png")
                print("等待标题输入框超时，已截图")


            # 填写标题
            title_input = page.locator("input[placeholder*='标题'], input[placeholder*='填写标题']").first
            if title_input.is_visible():
                title_input.fill(title)
                time.sleep(1)
            else:
                page.screenshot(path=f"{screenshot_dir}/title_input_error_{int(time.time())}.png")
                print("未找到标题输入框，已截图")

            # 填写正文
            content_editor = page.locator(".DraftEditor-root, .editor, textarea[placeholder*='正文'], textarea[placeholder*='内容'], div[contenteditable='true']").first
            if content_editor.is_visible():
                content_editor.click()
                time.sleep(1)
                page.keyboard.type(note_content, delay=50)
                time.sleep(2)
            else:
                page.screenshot(path=f"{screenshot_dir}/content_editor_error_{int(time.time())}.png")
                print("未找到正文编辑器，已截图")

            # 发布
            publish_btn = page.locator("button:has-text('发布'), .publish-btn, [data-testid='publish-btn']").first
            if publish_btn.is_visible():
                publish_btn.click()
                print("已点击发布按钮，等待结果...")
                time.sleep(15)
                # 检查是否发布成功
                if page.get_by_text("发布成功").is_visible() or page.get_by_text("内容已发布").is_visible():
                    print("发布成功！")
                else:
                    page.screenshot(path=f"{screenshot_dir}/publish_fail_{int(time.time())}.png")
                    print("发布失败，已截图")
            else:
                page.screenshot(path=f"{screenshot_dir}/publish_btn_error_{int(time.time())}.png")
                print("未找到发布按钮，已截图")
        except Exception as e:
            page.screenshot(path=f"{screenshot_dir}/exception_{int(time.time())}.png")
            print(f"发布过程中发生异常，已截图: {e}")
        # 不关闭浏览器，方便人工排查

if __name__ == "__main__":
    # 默认发布 note_0.txt 和 note_0_img_*.png
    test_publish(note_index=0) 