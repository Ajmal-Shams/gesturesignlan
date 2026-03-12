"""Test if direct HaGRID class download works."""
import urllib.request
url = "https://rndml-team-cv.obs.ru-moscow-1.hc.sbercloud.ru/datasets/hagrid/hagrid_dataset_new_554800/hagrid_dataset/call.zip"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-1023"})
    r = urllib.request.urlopen(req, timeout=15)
    data = r.read()
    print(f"Status: {r.status}")
    print(f"Got {len(data)} bytes")
    print(f"Content-Type: {r.headers.get('Content-Type')}")
    print(f"Content-Length: {r.headers.get('Content-Length')}")
    content_range = r.headers.get('Content-Range', 'none')
    print(f"Content-Range: {content_range}")
    print("Direct HaGRID download WORKS!")
except Exception as e:
    print(f"Failed: {e}")
