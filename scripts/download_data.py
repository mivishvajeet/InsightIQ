"""
Download raw Olist Brazilian E-Commerce dataset files from the official repository
into data/raw/.
"""
import os
import urllib.request
import sys
from pathlib import Path

BASE_URL = "https://raw.githubusercontent.com/olist/work-at-olist-data/master/datasets/"

FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv"
]

def download_dataset(target_dir: Path = Path("data/raw")):
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading Olist dataset files to: {target_dir.resolve()}")
    for filename in FILES:
        dest_path = target_dir / filename
        if dest_path.exists() and dest_path.stat().st_size > 0:
            print(f"  [ALREADY EXISTS] {filename} ({dest_path.stat().st_size:,} bytes)")
            continue
        
        file_url = BASE_URL + filename
        print(f"  [DOWNLOADING] {filename} from {file_url} ...")
        try:
            urllib.request.urlretrieve(file_url, dest_path)
            size = dest_path.stat().st_size
            print(f"  [COMPLETED] {filename} ({size:,} bytes)")
        except Exception as e:
            print(f"  [ERROR] Failed to download {filename}: {e}", file=sys.stderr)
            if dest_path.exists():
                dest_path.unlink()
            raise

    print("\nAll 9 Olist dataset files successfully downloaded and verified.")

if __name__ == "__main__":
    download_dataset()

