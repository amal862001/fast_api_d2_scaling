# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime
FROM python:3.13-slim AS runtime

WORKDIR /app

# copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# copy app code
COPY . .

# create uploads directory
RUN mkdir -p /app/uploads

# expose port
EXPOSE 8000

# run startup script
CMD ["sh", "startup.sh"]