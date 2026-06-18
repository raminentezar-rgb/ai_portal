import requests

def ocr_space_file(filename, api_key='helloworld', language='eng'):
    payload = {'isOverlayRequired': False,
               'apikey': api_key,
               'language': language,
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={'filename': f},
                          data=payload,
                          )
    return r.json()

try:
    with open("test.jpg", "wb") as f:
        f.write(requests.get("https://raw.githubusercontent.com/tesseract-ocr/test/master/testing/phototest.tif").content)
    print(ocr_space_file('test.jpg'))
except Exception as e:
    print(e)
