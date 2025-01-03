files = ["stream_downloader_telegram.py", "upload_to_telegram.py"]

if __name__ == "__main__":
    for filename in files:
        with open(filename, 'r') as file:
            code = file.read()
            exec(code)
        
    
    
    
    
