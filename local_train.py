import os
import sys

# 1. Setup Environment
# Ensure the script can find 'shared' and 'services' folders
sys.path.append(os.getcwd())

from dotenv import load_dotenv
load_dotenv() # Load production secrets from .env

from shared.ml.training import train_job_all_coins
import colorama
from colorama import Fore, Style

colorama.init()

def run_local_training():
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== CryptoQuant Local Trainer ==={Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Target Storage: {os.getenv('S3_ENDPOINT_URL', 'Local')}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Target Database: {os.getenv('DB_URL', 'Local').split('@')[-1] if '@' in os.getenv('DB_URL', '') else 'Local'}{Style.RESET_ALL}")
    print("-" * 40)
    
    try:
        # This will fetch data, train, and UPLOAD to Supabase
        train_job_all_coins()
        
        print("-" * 40)
        print(f"{Fore.GREEN}{Style.BRIGHT}SUCCESS: All models trained and pushed to Production Supabase!{Style.RESET_ALL}")
        print(f"{Fore.CYAN}You can now check your live website at Vercel.{Style.RESET_ALL}\n")
        
    except Exception as e:
        print(f"\n{Fore.RED}CRITICAL ERROR: {str(e)}{Style.RESET_ALL}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_local_training()
