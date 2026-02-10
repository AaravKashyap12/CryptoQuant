import pandas as pd
from src.data_fetcher import get_current_price

# Define coins and currencies
COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]
CURRENCIES = ["USD", "INR", "EUR", "GBP", "AUD", "CAD", "JPY"]

def main():
    print(f"\n{'COIN':<8} {'CURR':<6} {'PRICE':<15} {'NOTE'}")
    print("-" * 60)

    for coin in COINS:
        for currency in CURRENCIES:
            # Construct symbol
            target_symbol = f"{coin}{currency}"
            if currency == 'USD':
                target_symbol = f"{coin}USDT"
            
            # Use the new smart fetcher
            price = get_current_price(target_symbol)
            
            status = "OK" if price else "FAIL"
            price_str = f"{price:<15.2f}" if price else "N/A"
            
            print(f"{coin:<8} {currency:<6} {price_str} {status}")

if __name__ == "__main__":
    main()
