import pandas as pd
from src.data_fetcher import get_current_price, get_conversion_rate

# Define coins and currencies
COINS = ["BTC", "ETH", "BNB", "SOL", "ADA"]
CURRENCIES = ["USD", "INR", "EUR", "GBP"]

def main():
    print(f"{'COIN':<10} {'CURRENCY':<10} {'PRICE':<20} {'SOURCE':<10}")
    print("-" * 60)

    for coin in COINS:
        for currency in CURRENCIES:
            # 1. Try Direct Pair
            pair_symbol = f"{coin}{currency}"
            if currency == 'USD':
                pair_symbol = f"{coin}USDT"
            
            price = get_current_price(pair_symbol)
            source = "Direct"

            # 2. Fallback if needed
            if price is None:
                # Fetch USDT price
                usdt_price = get_current_price(f"{coin}USDT")
                if usdt_price:
                    rate = get_conversion_rate(currency)
                    price = usdt_price * rate
                    source = f"Converted (Rate: {rate:.2f})"
                else:
                    price = 0.0
                    source = "Failed"
            
            # Format price
            if currency == 'INR':
                formatted_price = f"INR {price:,.2f}"
            elif currency == 'USD':
                formatted_price = f"USD {price:,.2f}"
            elif currency == 'EUR':
                formatted_price = f"EUR {price:,.2f}"
            elif currency == 'GBP':
                formatted_price = f"GBP {price:,.2f}"
            else:
                formatted_price = f"{price:,.2f}"

            print(f"{coin:<10} {currency:<10} {formatted_price:<20} {source:<10}")

if __name__ == "__main__":
    main()
