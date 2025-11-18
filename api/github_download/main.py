from fastapi import FastAPI
from src.github_client.routes import router as github_router
from src.pr_download.routes import router as pr_download_router
from src.pr_status.routes import router as pr_status_router

app = FastAPI(
    title="GitHub Download API",
    description="API for analyzing GitHub repositories and pull requests",
    version="1.0.0"
)

app.include_router(github_router, prefix="/api/v1/github", tags=["github"])
app.include_router(pr_download_router, prefix="/api/v1/pr", tags=["pr-download"])
app.include_router(pr_status_router, prefix="/api/v1/pr", tags=["pr-status"])

@app.get("/")
async def root():
    return {"message": "GitHub Download API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)