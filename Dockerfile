# 1. Use official Python image
FROM python:3.10-slim

# 2. Environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Set working directory
WORKDIR /app

# 4. Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt

# 6. Copy the entire project into the container
COPY . .

# 7. Collect static files
RUN python manage.py collectstatic --noinput

# 8. Expose port 8080 (used by Railway)
EXPOSE 8080

# 9. Start Django with Gunicorn
CMD ["gunicorn", "hair_project.wsgi:application", "--bind", "0.0.0.0:8080"]
