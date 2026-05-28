"""
assets/create_sample_excel.py
Run this once to generate a sample Excel template.
"""

import pandas as pd
import os

data = {
    'name'     : ['Bengkulu','Jakarta','Medan','Kuala Lumpur','Surabaya','Makassar'],
    'latitude' : [  -3.800,  -6.210,   3.590,        3.140,   -7.250,    -5.130],
    'longitude': [ 102.270, 106.850,  98.670,      101.690,  112.750,   119.420],
}

df = pd.DataFrame(data)
out = os.path.join(os.path.dirname(__file__), "sample_input.xlsx")
df.to_excel(out, index=False)
print(f"Sample Excel saved: {out}")
