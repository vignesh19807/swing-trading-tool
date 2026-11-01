with open('backend/data_pipeline/research_market_data_filter.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_holiday = '    # 2. Known holiday\n    is_known_holiday = out["date"].isin(KNOWN_EXCHANGE_HOLIDAYS)'
new_holiday = '''    # 2. Known holiday (normalize to YYYY-MM-DD string series for robust comparison)
    date_strs = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    is_known_holiday = date_strs.isin(KNOWN_EXCHANGE_HOLIDAYS)'''

assert old_holiday in text, "old_holiday not found"
text = text.replace(old_holiday, new_holiday, 1)

with open('backend/data_pipeline/research_market_data_filter.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Successfully fixed date normalization in research_market_data_filter.py")

