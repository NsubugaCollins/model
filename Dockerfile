# --- STAGE 1: Builder ---
# Use a full Python image to ensure all dependencies compile correctly.
FROM python:3.11 as builder

# Set environment variables for non-interactive commands
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy the requirements file first to utilize Docker layer caching
COPY requirements.txt .

# Install dependencies. We use --no-cache-dir to minimize size.
# Note: psycopg2 often requires build dependencies, which are available in this base image.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire Django project code
COPY . .

# Optional: Collect static files if you are serving them from the container (common with Whitenoise)
RUN python manage.py collectstatic --noinput


# --- STAGE 2: Production Runtime ---
# Use the highly optimized Python slim image for the final, lean production container.
# This image is much smaller as it lacks development tools.
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only the compiled Python packages and static files from the builder stage:
# 1. Python environment/dependencies
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# 2. Application code and static files
COPY --from=builder /app /app

# Expose the default port for web services on Railway
EXPOSE 8000

# Define the command to run your Django application using Gunicorn (recommended WSGI server)
# You need to replace 'your_project_name.wsgi' with your actual Django project name.
# Ensure Gunicorn and Whitenoise (if used) are in your requirements.txt
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "your_project_name.wsgi:application"]