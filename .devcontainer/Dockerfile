FROM python:3.12-slim

# Install Tesseract OCR + German and English language data, plus build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
        imagemagick \
        tesseract-ocr \
        tesseract-ocr-deu \
        tesseract-ocr-eng \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for development
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=${USER_UID}
RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

WORKDIR /workspace

# Install Python dependencies eagerly so the container starts fast
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

USER ${USERNAME}
