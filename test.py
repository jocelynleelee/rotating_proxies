import concurrent.futures
import requests

url = 'https://example.com'

def send_request(proxy_url):
    try:
        response = requests.get(url, proxies={'http': proxy_url}, timeout=10)

        if response.status_code == 200:
            print(f"Request using {proxy_url} succeeded: {response.text[:50]}")
        else:
            print(f"Request using {proxy_url} failed with status code {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Request error using {proxy_url}: {e}")

def main():
    # Read proxy URLs from the text file
    with open('proxy_list.txt', 'r') as file:
        proxy_list = [line.strip() for line in file if line.strip()]

    proxy_list = proxy_list[:1]
    # Create a ThreadPoolExecutor for concurrent execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(proxy_list)) as executor:
        # Submit tasks for each proxy in the list
        executor.map(send_request, proxy_list)

if __name__ == "__main__":
    main()
