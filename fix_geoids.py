import pandas as pd

paths = [
    'data/processed/acs_tract_data.csv',
    'data/processed/evictionlab_tract_data.csv'
]

for path in paths:
    df = pd.read_csv(path, dtype={'GEOID': str})
    df['GEOID'] = df['GEOID'].str.zfill(11)
    df.to_csv(path, index=False)
    print(f'✅ Fixed {path} — sample: {df["GEOID"].iloc[0]}')
