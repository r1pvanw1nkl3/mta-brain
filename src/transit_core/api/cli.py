import uvicorn


def main():
    uvicorn.run("transit_core.api.main:app", host="127.0.0.1", port=8000, reload=True)
