FROM python:3.11-slim

# Typstと日本語フォント（IPAフォント・Notoフォント）をインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    xz-utils \
    fonts-noto-cjk \
    fonts-ipafont-gothic \
    fonts-ipaexfont-gothic \
    fontconfig \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Typstバイナリのダウンロード・配置
RUN curl -LO https://github.com/typst/typst/releases/download/v0.12.0/typst-x86_64-unknown-linux-musl.tar.xz \
    && tar -xvf typst-x86_64-unknown-linux-musl.tar.xz \
    && mv typst-x86_64-unknown-linux-musl/typst /usr/local/bin/typst \
    && rm -rf typst-x86_64-unknown-linux-musl*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
