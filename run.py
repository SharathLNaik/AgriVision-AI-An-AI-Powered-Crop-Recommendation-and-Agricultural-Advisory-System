import os
import sys
import subprocess
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_app():
    print("==========================================================")
    print("   AGRIVISION AI - SOUTH INDIA CROP & YIELD SYSTEM       ")
    print("==========================================================")
    
    # 1. Check & Download Datasets
    data_dir = os.path.join(BASE_DIR, 'data')
    if not os.path.exists(os.path.join(data_dir, 'south_india_crop_production.csv')):
        print("[Step 1/3] Downloading authentic South Indian datasets...")
        subprocess.run([sys.executable, 'download_datasets.py'], check=True)
    else:
        print("[Step 1/3] South Indian datasets verified.")

    # 2. Check & Train ML Models
    model_dir = os.path.join(BASE_DIR, 'models')
    if not os.path.exists(os.path.join(model_dir, 'crop_rf.pkl')):
        print("[Step 2/3] Training Machine Learning Models (Random Forest, SVM, DNN)...")
        subprocess.run([sys.executable, 'train_models.py'], check=True)
    else:
        print("[Step 2/3] Trained Machine Learning models verified.")

    # 3. Launch Flask Server
    print("[Step 3/3] Starting AgriVision AI Flask Web Application...")
    print("Serving on http://127.0.0.1:5000")
    print("==========================================================")

    import app
    app.app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    run_app()
