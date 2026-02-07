#!/usr/bin/env python3
import csv
import json
import os

def parse_portfolio(csv_path):
    holdings = []
    total_value = 0
    total_gain_today = 0
    total_gain_all = 0
    total_cost_basis = 0
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = (row.get('Symbol') or '').strip()
            if not symbol or symbol.startswith('"'):
                continue
                
            # Handle cash
            if '**' in symbol:
                val = (row.get('Current Value') or '$0').replace('$', '').replace(',', '')
                try:
                    cash_val = float(val) if val else 0
                    holdings.append({
                        'symbol': 'CASH',
                        'description': 'Cash',
                        'quantity': None,
                        'price': None,
                        'value': cash_val,
                        'today_gain': 0,
                        'today_gain_pct': 0,
                        'total_gain': 0,
                        'total_gain_pct': 0,
                        'pct_of_account': float((row.get('Percent Of Account') or '0%').replace('%', ''))
                    })
                    total_value += cash_val
                except:
                    pass
                continue
            
            try:
                def clean_num(s):
                    if not s:
                        return 0
                    return float(s.replace('$', '').replace(',', '').replace('+', '').replace('%', ''))
                
                value = clean_num(row.get('Current Value'))
                today_gain = clean_num(row.get("Today's Gain/Loss Dollar"))
                today_gain_pct = clean_num(row.get("Today's Gain/Loss Percent"))
                total_gain = clean_num(row.get('Total Gain/Loss Dollar'))
                total_gain_pct = clean_num(row.get('Total Gain/Loss Percent'))
                cost_basis = clean_num(row.get('Cost Basis Total'))
                quantity = clean_num(row.get('Quantity'))
                price = clean_num(row.get('Last Price'))
                pct_of_account = clean_num(row.get('Percent Of Account'))
                
                holdings.append({
                    'symbol': symbol,
                    'description': (row.get('Description') or '')[:30],
                    'quantity': quantity,
                    'price': price,
                    'value': value,
                    'today_gain': today_gain,
                    'today_gain_pct': today_gain_pct,
                    'total_gain': total_gain,
                    'total_gain_pct': total_gain_pct,
                    'pct_of_account': pct_of_account
                })
                
                total_value += value
                total_gain_today += today_gain
                total_gain_all += total_gain
                total_cost_basis += cost_basis
            except Exception as e:
                continue
    
    # Sort by value descending
    holdings.sort(key=lambda x: x['value'], reverse=True)
    
    return {
        'holdings': holdings,
        'total_value': round(total_value, 2),
        'today_gain': round(total_gain_today, 2),
        'today_gain_pct': round((total_gain_today / total_value * 100) if total_value else 0, 2),
        'total_gain': round(total_gain_all, 2),
        'total_gain_pct': round((total_gain_all / total_cost_basis * 100) if total_cost_basis else 0, 2),
        'cost_basis': round(total_cost_basis, 2)
    }

if __name__ == '__main__':
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'portfolio.csv')
    if os.path.exists(csv_path):
        portfolio = parse_portfolio(csv_path)
        print(json.dumps(portfolio, indent=2))
    else:
        print("No portfolio.csv found")
