# Module Import Fix for Coolify Deployment

## Problem
The application was failing to start in Coolify with the error:
```
ModuleNotFoundError: No module named 'src.app'
```

This error occurred when Gunicorn tried to import `src.app:app` but Python couldn't resolve the `src` module.

## Root Cause
The issue was caused by Python's module resolution system. When running `gunicorn src.app:app` in the Docker container:

1. The working directory is set to `/app`
2. Python's `sys.path` doesn't automatically include the current working directory for module imports
3. Therefore, Python can't find the `src` module when trying to import `src.app`

## Why It Worked Locally
- Local development environments often have the project root in the Python path
- IDEs typically configure this automatically
- Or the application might be run differently locally (e.g., `python src/app.py`)

## Solution
Added `ENV PYTHONPATH=/app` to both Dockerfiles:

### Changes Made

**Dockerfile:**
```dockerfile
WORKDIR /app

# Set PYTHONPATH to include the app directory for module resolution
ENV PYTHONPATH=/app

COPY requirements.txt .
# ... rest of file
```

**Dockerfile.prod:**
```dockerfile
# Environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV ENV=production
ENV PYTHONPATH=/app
ENV PATH="/home/appuser/.local/bin:/root/.local/bin:${PATH}"
```

## Alternative Solutions
If you prefer not to modify the Dockerfiles, you could also:

1. **Change the Gunicorn command** to:
   ```dockerfile
   CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
   ```
   And run from the `src` directory.

2. **Use a startup script** that sets PYTHONPATH before running Gunicorn.

3. **Create a proper Python package** with a `setup.py` and install it in the container.

## Verification
After applying the fix, rebuild your Docker image and deploy to Coolify. The module import error should be resolved.