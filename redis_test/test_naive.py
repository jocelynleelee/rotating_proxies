
import pydnsbl


def validate(proxy_url):
    ip_checker = pydnsbl.DNSBLIpChecker()
    try:
        res = ip_checker.check(proxy_url)
    except Exception as e:
        print(str(e))
    return res


def main():
    proxy_url = "178.128.113.118"
    res = validate(proxy_url)
    print(res)

if __name__ == "__main__":
    main()
