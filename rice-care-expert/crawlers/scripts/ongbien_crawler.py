import requests
from bs4 import BeautifulSoup
import os
import re

class RiceDataCrawler:
    def __init__(self):
        # Đường dẫn dựa trên cấu trúc thư mục bạn cung cấp
        self.raw_html_path = "../../data/raw/html"
        self.processed_md_path = "../../data/processed/markdown"

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(self.raw_html_path, exist_ok=True)
        os.makedirs(self.processed_md_path, exist_ok=True)

    def clean_filename(self, text):
        """Tạo tên file an toàn từ tiêu đề"""
        text = re.sub(r'[^\w\s-]', '', text).strip().lower()
        return text.replace(' ', '_')

    def crawl(self, url):
        # Nâng cấp headers để tránh bị bot detection
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                print(f"❌ Lỗi truy cập: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Lấy tiêu đề
            title_tag = soup.find('h1')
            title = title_tag.get_text(strip=True) if title_tag else "Unknown_Title"
            safe_name = self.clean_filename(title)

            # 2. Tìm vùng nội dung (Thử nhiều class phổ biến của trang ongbien.vn)
            # Trang này thường dùng class 'detail-content' hoặc 'content-detail'
            content_div = soup.find('div', class_=re.compile(r'detail-content|content-detail|post-content'))

            # Nếu vẫn không thấy, tìm thẻ <article> hoặc div có nhiều thẻ <p> nhất
            if not content_div:
                content_div = soup.find('article')

            if not content_div:
                # Tìm div bất kỳ chứa nhiều hơn 3 thẻ <p> (vùng nội dung bài viết)
                all_divs = soup.find_all('div')
                content_div = max(all_divs, key=lambda d: len(d.find_all('p')))

            if not content_div or len(content_div.find_all('p')) < 2:
                print("⚠️ Vẫn không tìm thấy vùng nội dung chính. Có thể trang web yêu cầu JavaScript.")
                # Lưu lại file html lỗi để kiểm tra xem web trả về cái gì
                with open("error_debug.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                return

            # 3. Lưu file HTML GỐC
            with open(os.path.join(self.raw_html_path, f"{safe_name}.html"), "w", encoding="utf-8") as f:
                f.write(response.text)

            # 4. Chuyển đổi sang Markdown
            markdown_content = f"# {title}\n\n"
            markdown_content += f"*Nguồn: {url}*\n\n---\n\n"

            # Chỉ lấy các thẻ chứa thông tin hữu ích trong vùng content
            for element in content_div.find_all(['h2', 'h3', 'p', 'li']):
                # Loại bỏ các đoạn text rác (ví dụ: chia sẻ facebook, tag...)
                text = element.get_text(strip=True)
                if len(text) < 5: continue

                if element.name == 'h2':
                    markdown_content += f"## {text}\n\n"
                elif element.name == 'h3':
                    markdown_content += f"### {text}\n\n"
                elif element.name == 'li':
                    markdown_content += f"* {text}\n"
                else:
                    markdown_content += f"{text}\n\n"

            with open(os.path.join(self.processed_md_path, f"{safe_name}.md"), "w", encoding="utf-8") as f:
                f.write(markdown_content)

            print(f"✅ Đã xử lý xong: {title}")

        except Exception as e:
            print(f"🔥 Lỗi hệ thống: {e}")
if __name__ == "__main__":
    crawler = RiceDataCrawler()
    url_target = "https://ongbien.vn/ky-thuat-canh-tac/ky-thuat-trong-va-cham-soc-cay-lua-nhung-bien-phap-giup-tang-nang-suat-hieu-qua-65841dt.html"
    crawler.crawl(url_target)