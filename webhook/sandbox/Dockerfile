# docker run --rm my-app-image /path/to/your-executable

# Use a minimal base image with necessary utilities
# FROM alpine:latest
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies for YARA Python bindings and ps
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libmagic-dev \
    yara \
    procps diffutils

# Install the YARA Python bindings
RUN pip install argparse
RUN pip install yara-python 
RUN pip install EntropyAnalysis

COPY . .
RUN chmod +x benchmark.sh

# Start a shell, execute the binary from the command line, and then run ps
CMD ["/app/benchmark.sh"]
