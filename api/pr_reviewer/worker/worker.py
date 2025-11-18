import csv
import subprocess
import sys
import pandas as pd

def read_csv_file_with_pandas(file_path):
    """
    Reads a CSV file using pandas and returns a DataFrame.
    """
    try:
        df = pd.read_csv(file_path)
        print(f"--- Successfully read {file_path} with pandas ---")
        return df
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading CSV with pandas: {e}")
        sys.exit(1)

def run_subprocess_with_repo_url(repo_url):
    """
    Invokes main.py with the provided repository URL.
    """
    print(f"\n--- Invoking main.py for repository: {repo_url} ---")
    try:
        # Assuming main.py is in the same directory
        result = subprocess.run(
            [sys.executable, "main.py", repo_url],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"main.py Stdout:\n{result.stdout.strip()}")
        if result.stderr:
            print(f"main.py Stderr:\n{result.stderr.strip()}")
        print(f"--- main.py finished for {repo_url} ---")
    except subprocess.CalledProcessError as e:
        print(f"Error invoking main.py for {repo_url}: {e}")
        print(f"main.py Stdout:\n{e.stdout.strip()}")
        print(f"main.py Stderr:\n{e.stderr.strip()}")
    except FileNotFoundError:
        print("Error: 'main.py' or python executable not found. Ensure main.py is in the same directory and python is in your PATH.")



if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python worker.py <path_to_csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    df = read_csv_file_with_pandas(csv_file)

    if 'repo_url' in df.columns:
        for index, row in df.iterrows():
            repo_url = row['repo_url']
            run_subprocess_with_repo_url(repo_url)
    else:
        print("Error: 'repo_url' column not found in the CSV file.")
        sys.exit(1)