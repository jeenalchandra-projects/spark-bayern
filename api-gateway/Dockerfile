# =============================================================================
# Dockerfile — API Gateway
# =============================================================================
# WHAT A DOCKERFILE IS:
# A Dockerfile is a recipe for creating a Docker container.
# Think of a container as a sealed box that contains:
#   - The operating system (a minimal Linux)
#   - Python and all dependencies
#   - Our code
# This box runs identically on your Mac, on a colleague's Windows PC,
# and on Railway's servers. "It works on my machine" stops being a problem.
#
# HOW TO READ A DOCKERFILE:
# Each line is an instruction. Docker runs them top to bottom when building.
# =============================================================================

# FROM: Start from an existing base image.
# python:3.13-slim is an official Python image based on minimal Debian Linux.
# "slim" means it excludes unnecessary tools, keeping the image small and secure.
FROM python:3.13-slim

# WORKDIR: All following commands run from this directory inside the container.
# Like doing "cd /app" first.
WORKDIR /app

# COPY requirements.txt first — before copying the rest of the code.
# WHY: Docker caches each step. If requirements.txt hasn't changed,
# Docker skips the pip install step on rebuilds. This saves a lot of time.
COPY requirements.txt .

# RUN: Execute a shell command during the build.
# --no-cache-dir: Don't cache downloaded packages (keeps image smaller)
# --upgrade pip: Make sure pip itself is up to date
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# COPY: Now copy the rest of the application code into the container.
# The "." means "everything in the current directory on your Mac"
# The "/app" means "put it in /app inside the container"
COPY . .

# EXPOSE: Documents which port this container listens on.
# This is documentation — Docker doesn't actually open the port here.
# The actual port mapping happens in docker-compose.yml.
EXPOSE 8000

# CMD: The command that runs when the container starts.
# uvicorn: the server
# main:app: run the "app" object in "main.py"
# --host 0.0.0.0: listen on all network interfaces (required inside Docker)
# --port 8000: listen on port 8000
# --workers 1: use 1 worker process (enough for a demo)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
