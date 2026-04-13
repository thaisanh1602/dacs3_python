import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urljoin


class VAASFullCrawler:
    def __init__(self):
        self.raw_path = "../../data/raw/html"
        self.processed_path = "../../data/processed/markdown"
        # URL mục lục chính
        self.index_url = "https://vaas.vn/kienthuc/Caylua/06/index.htm"

        os.makedirs(self.raw_path, exist_ok=True)
        os.makedirs(self.processed_path, exist_ok=True)

    def clean_text(self, text):
        return re.sub(r'\s+', ' ', text).strip()

    def extract_logic(self, soup, url):
        """Phân tích nội dung để tách Khái niệm và Phòng trừ"""
        # Với cấu trúc bạn gửi, nội dung nằm trong thẻ <table> thứ 2 hoặc chứa <h2>
        main_table = soup.find('table', width="100%")
        if not main_table:
            main_table = soup.find('body')

        title = soup.find('h2').get_text(strip=True) if soup.find('h2') else "Tai_lieu_chua_dat_ten"

        markdown = f"# {title}\n\n*Nguồn: {url}*\n\n"

        # Lấy tất cả các đoạn văn bản
        paragraphs = main_table.find_all(['p', 'li', 'td'])

        current_section = "🔍 Khái niệm & Đặc điểm"
        markdown += f"## {current_section}\n"

        found_prevention = False
        for p in paragraphs:
            text = self.clean_text(p.get_text())
            if len(text) < 5 or "p align=" in str(p): continue  # Bỏ qua các icon điều hướng

            # Nếu gặp từ khóa PHÒNG TRỪ thì đổi mục
            if "PHÒNG TRỪ" in text.upper() or "BIỆN PHÁP" in text.upper():
                markdown += "\n## 🛡️ Cách phòng trừ & Điều trị\n"
                found_prevention = True
                continue

            # Thêm nội dung vào mục tương ứng
            if p.name == 'li' or text.startswith('-'):
                markdown += f"* {text}\n"
            else:
                markdown += f"{text}\n\n"

        return title, markdown

    def run(self):
        print(f"🚀 Đang quét mục lục tại: {self.index_url}")
        res = requests.get(self.index_url)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')

        # 1. Tìm tất cả các link bài viết (.htm) trong trang mục lục
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Lọc các link như '01_sauducthan.htm', '02_sauducthan2.htm'...
            if re.match(r'\d+.*\.htm', href):
                links.append(urljoin(self.index_url, href))

        # Loại bỏ link trùng
        links = list(set(links))
        print(f"🔍 Tìm thấy {len(links)} bài viết cần crawl.")

        # 2. Lặp qua từng link để lấy nội dung
        for link in sorted(links):
            try:
                response = requests.get(link)
                response.encoding = 'utf-8'
                article_soup = BeautifulSoup(response.text, 'html.parser')

                title, md_content = self.extract_logic(article_soup, link)
                safe_name = re.sub(r'\W+', '_', title).lower()

                # Lưu Raw HTML
                with open(os.path.join(self.raw_path, f"{safe_name}.html"), "w", encoding="utf-8") as f:
                    f.write(response.text)

                # Lưu Processed Markdown
                with open(os.path.join(self.processed_path, f"{safe_name}.md"), "w", encoding="utf-8") as f:
                    f.write(md_content)

                print(f"✅ Đã xử lý xong: {title}")

            except Exception as e:
                print(f"❌ Lỗi tại link {link}: {e}")


if __name__ == "__main__":
    crawler = VAASFullCrawler()
    crawler.run()