# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project files into the container
COPY . /app/

# Expose the port the app runs on
EXPOSE 8000

# Set the default command to run the Django development server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]