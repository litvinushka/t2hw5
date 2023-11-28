import aiohttp
import asyncio
import argparse
import json
import datetime
import websockets
import aiofile
from pathlib import Path

async def fetch_currency_data(date, session):
    url = f'https://api.privatbank.ua/p24api/exchange_rates?json&date={date}'
    async with session.get(url) as response:
        return await response.json()

async def get_exchange_rates(days):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_currency_data((datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%d.%m.%Y"), session) for i in range(days)]
        results = await asyncio.gather(*tasks)

        formatted_results = []
        for result in results:
            currency_data = {'date': result['date']}
            currencies = result['exchangeRate']
            for currency in currencies:
                if currency['currency'] in ['EUR', 'USD', 'GBP', 'JPY']:  
                    currency_data[currency['currency']] = {
                        'sale': currency['saleRateNB'],
                        'purchase': currency['purchaseRateNB']
                    }
            formatted_results.append(currency_data)

        return formatted_results

async def handle_exchange_command(websocket, path):
    async for message in websocket:
        if message.startswith("exchange"):
            parts = message.split()
            if len(parts) == 2 and parts[1].isdigit():
                days = int(parts[1])
                exchange_rates = await get_exchange_rates(days)
                await websocket.send(json.dumps(exchange_rates, indent=2, ensure_ascii=False))
                async with aiofile.AIOFile('exchange_logs.txt', 'a') as afp:
                    await afp.write(f"Command 'exchange {days}' executed at {datetime.datetime.now()}\n")
            else:
                await websocket.send("Invalid command format. Please use 'exchange N' where N is the number of days.")

def main():
    parser = argparse.ArgumentParser(description='Get exchange rates of selected currencies from PrivatBank for the last N days.')
    parser.add_argument('days', type=int, help='Number of days to retrieve exchange rates for (up to 10 days).')
    parser.add_argument('--currencies', nargs='+', default=['EUR', 'USD'], help='List of currencies to retrieve (default: EUR USD).')

    args = parser.parse_args()

    if args.days <= 0 or args.days > 10:
        print('Error: Invalid number of days. Please enter a value between 1 and 10.')
        return

    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(get_exchange_rates(args.days))

    print(json.dumps(results, indent=2, ensure_ascii=False))

    start_server = websockets.serve(handle_exchange_command, "localhost", 8765)
    loop.run_until_complete(start_server)
    loop.run_forever()

if __name__ == '__main__':
    main()
