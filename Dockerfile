FROM python:3.11-slim

# تثبيت المتطلبات الأساسية
RUN apt update && apt install -y ffmpeg

# إنشاء مجلد التطبيق
WORKDIR /app

# نسخ الملفات
COPY . .

# تثبيت مكتبات Python
RUN pip install -r requirements.txt

# تحديد الأمر عند التشغيل
CMD ["python3", "main.py"]
