FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Streamlit port
EXPOSE 8501

ENTRYPOINT ["./entrypoint.sh"]
