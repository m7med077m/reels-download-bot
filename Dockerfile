FROM python:3.11-slim

# تثبيت ffmpeg
RUN apt update && apt install -y ffmpeg

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ كل الملفات من repo إلى داخل /app
COPY . .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# تشغيل البوت
CMD ["python3", "main.py"]
