import pytest
import subprocess
import time
import sys
import os
import requests
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page


class TestServer:
    """Helper class to manage test server lifecycle."""
    
    def __init__(self):
        self.process = None
        self.base_url = "http://localhost:8001"
    
    def start(self):
        """Start the FastAPI server for testing."""
        # First check if server is already running
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            if response.status_code == 200:
                print("Server is already running, using existing instance...")
                return
        except requests.exceptions.RequestException:
            pass  # Server not running, we'll start it
        
        print("Starting FastAPI server for e2e tests...")
        
        # Change to the project directory
        project_dir = "/home/tyler/is601/module13_assignment"
        
        # Start the server in the background
        self.process = subprocess.Popen(
            ["/home/tyler/is601/module13_assignment/venv/bin/python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001"],
            cwd=project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for server to start
        print("Waiting for server to start...")
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    print("Server started successfully!")
                    return
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        
        # If we get here, server didn't start properly
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(f"Server failed to start. STDOUT: {stdout.decode()}, STDERR: {stderr.decode()}")
        else:
            raise RuntimeError("Server took too long to start")
    
    def stop(self):
        """Stop the FastAPI server."""
        if self.process:
            print("Stopping FastAPI server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

@pytest.fixture(scope="session")
def test_server():
    """Session-scoped fixture to start and stop the test server."""
    server = TestServer()
    server.start()
    yield server
    server.stop()

@pytest.fixture(scope="session")
def playwright():
    """Session-scoped Playwright fixture."""
    with sync_playwright() as p:
        yield p

@pytest.fixture(scope="session")
def browser(playwright: Playwright):
    """Session-scoped browser fixture."""
    browser = playwright.chromium.launch(
        headless=os.getenv("HEADLESS", "true").lower() == "true",
        args=["--no-sandbox", "--disable-dev-shm-usage"]
    )
    yield browser
    browser.close()

@pytest.fixture
def context(browser: Browser):
    """Function-scoped browser context fixture."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
    )
    yield context
    context.close()

@pytest.fixture
def page(context: BrowserContext, test_server: TestServer):
    """Function-scoped page fixture."""
    page = context.new_page()
    page.set_default_timeout(30000)  # 30 seconds
    yield page
