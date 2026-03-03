# Use the official Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port (Cloud Run expects 8080 by default, but we bind to PORT env)
EXPOSE 8080

# Run the API with gunicorn for production stability
# We use 1 worker and multiple threads since the Gemini API is I/O bound
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
