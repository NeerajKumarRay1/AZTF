import os
import urllib.request

def download_file(url, output_path):
    print(f"Downloading {url} to {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    try:
        # Set User-Agent to avoid potential HTTP blockings
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response:
            with open(output_path, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Successfully downloaded {os.path.basename(output_path)} ({os.path.getsize(output_path)} bytes)")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def main():
    # Define dataset files and their direct download URLs
    datasets = {
        "nsl_kdd": {
            "KDDTrain+.txt": "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt",
            "KDDTest+.txt": "https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt"
        },
        "unsw_nb15": {
            "UNSW_NB15_training-set.csv": "https://raw.githubusercontent.com/Nir-J/ML-Projects/master/UNSW-Network_Packet_Classification/UNSW_NB15_training-set.csv",
            "UNSW_NB15_testing-set.csv": "https://raw.githubusercontent.com/Nir-J/ML-Projects/master/UNSW-Network_Packet_Classification/UNSW_NB15_testing-set.csv"
        },
        "cicids2017": {
            "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "https://raw.githubusercontent.com/SHUBHAMRAWAT-25/DDOS-attack-detection-using-random-forest-algorithm/master/Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv"
        }
    }

    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    for dataset_name, files in datasets.items():
        print(f"\n--- Downloading {dataset_name.upper()} Dataset ---")
        for file_name, url in files.items():
            out_path = os.path.join(base_dir, dataset_name, file_name)
            if os.path.exists(out_path):
                print(f"{file_name} already exists. Skipping download.")
            else:
                download_file(url, out_path)

if __name__ == "__main__":
    main()
