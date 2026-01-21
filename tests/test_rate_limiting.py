import httpx
import time

URL = "http://localhost:8000/api/v1/chat/title"

def test_rate_limit():
    print(f"Testing rate limit on {URL}...")
    for i in range(25):
        try:
            response = httpx.post(URL, json={"query": "test"})
            print(f"Request {i+1}: {response.status_code}")
            if response.status_code == 429:
                print("\nSUCCESS: Rate limit triggered! (429 Too Many Requests)")
                return
        except Exception as e:
            print(f"Error: {e}")
            break
    print("\nFAILED: Rate limit not triggered or server not running.")

if __name__ == "__main__":
    test_rate_limit()
