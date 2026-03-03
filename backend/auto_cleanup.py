
import os
import time
import glob

UPLOAD_FOLDER = "/tmp/relab_uploads"
REPORT_FOLDER = "/tmp/relab_reports"
MAX_AGE_HOURS = 24

def cleanup_old_files():
    now = time.time()
    max_age = MAX_AGE_HOURS * 3600
    count = 0
    size = 0
    
    for folder in [UPLOAD_FOLDER, REPORT_FOLDER]:
        for pattern in ["*.mov", "*.mp4", "*.avi", "*.html"]:
            for f in glob.glob(os.path.join(folder, pattern)):
                try:
                    if now - os.path.getmtime(f) > max_age:
                        size += os.path.getsize(f)
                        os.remove(f)
                        count += 1
                except: pass
    
    if count > 0:
        print(f"[Clean] {count} files, freed {size/1024/1024:.1f}MB")

if __name__ == "__main__":
    cleanup_old_files()
