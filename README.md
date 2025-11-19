# toon_plus
Toon Plus format implementation based on Toon + CSV format.
## Token-Oriented Object Notation Plus (TOON PLUS)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/zoreu/toon_plus/blob/main/toon_test.ipynb)

```python
from toon_plus import toon_plus
data = {
    "users": [
        {"name": "Ana", "age": None, "active": False, "country": "Brasil"},
        {"name": "Bruno", "age": 34, "active": True, "country": "Portugal"}
    ],
    "products": [
        {"id": 1, "name": "Caneta", "price": 2.5},
        {"id": 2, "name": "Caderno", "price": 15.0}]
    }
data2 = [
    {"name": "Ana", "age": None, "active": False},{"name": "Bruno", "age": 34, "active": True}
    ]
data3 = {'name': 'John', 'age': 30, 'is_student': False}
data4 = {"Users": {"name": "Alice", "age": 25}}
data5 = {"Users": {"name": "Alice", "age": 25, "jobs": ['Engineer', 'Writer']}}
data6 = {"Users": {"name": "Alice", "age": 25, "address": {"city": "Wonderland", "zip": "12345"}}}
data7 = [1,2,4,5,6]
toon_text = toon_plus.encode(data)
print("Toon Plus Format:")
print(toon_text)
dict_data = toon_plus.decode(toon_text)
print("\nDecoded Dictionary:")
print(dict_data)
print("\nDecoded json:")
json_data = toon_plus.decode2json(toon_text)
print(json_data)
print("\nToon Plus Format (simple array):")
toon_text2 = toon_plus.encode(data2)
print(toon_text2)
dict_data2 = toon_plus.decode(toon_text2)
print("\nDecoded Dictionary (simple array):")
print(dict_data2)  
print("\nDecoded json (simple array):")
json_data2 = toon_plus.decode2json(toon_text2)
print(json_data2)  
toon_text3 = toon_plus.encode(data3)
print("\nToon Plus Format (simple object):")
print(toon_text3) 
print("\nDecoded Dictionary (simple object):")
dict_data3 = toon_plus.decode(toon_text3)
print(dict_data3)
print("\nDecoded json (simple object):")
json_data3 = toon_plus.decode2json(toon_text3)
print(json_data3) 
print("\n=== dict inside dict (named simple object) ===")
dict_in_dict = toon_plus.encode(data4)
print(dict_in_dict)
print("\ndecoded (named simple object):", toon_plus.decode(dict_in_dict))    
print("\n=== list inside dict ===")
list_in_dict = toon_plus.encode(data5)
print(list_in_dict)
print("\ndecoded (list inside dict):", toon_plus.decode(list_in_dict))
print("\n=== dict inside dict inside dict ===")
dict_in_dict_in_dict = toon_plus.encode(data6)
print(dict_in_dict_in_dict)        
print("\ndecoded (dict inside dict inside dict):", toon_plus.decode(dict_in_dict_in_dict))
print("\n=== simple list of numbers ===")
list_numbers = toon_plus.encode(data7)
print(list_numbers)
print("\ndecoded (simple list of numbers):", toon_plus.decode(list_numbers))
```
```bash
# OUTPUT

Toon Plus Format:
users{name,age,active,country}
Ana,null,false,Brasil
Bruno,34,true,Portugal

products{id,name,price}
1,Caneta,2.5
2,Caderno,15.0

Decoded Dictionary:
{'users': [{'name': 'Ana', 'age': None, 'active': False, 'country': 'Brasil'}, {'name': 'Bruno', 'age': 34, 'active': True, 'country': 'Portugal'}], 'products': [{'id': 1, 'name': 'Caneta', 'price': 2.5}, {'id': 2, 'name': 
'Caderno', 'price': 15.0}]}

Decoded json:
{"users": [{"name": "Ana", "age": null, "active": false, "country": "Brasil"}, {"name": "Bruno", "age": 34, "active": true, "country": "Portugal"}], "products": [{"id": 1, "name": "Caneta", "price": 2.5}, {"id": 2, "name": 
"Caderno", "price": 15.0}]}

Toon Plus Format (simple array):
{name,age,active}
Ana,null,false
Bruno,34,true

Decoded Dictionary (simple array):
[{'name': 'Ana', 'age': None, 'active': False}, {'name': 'Bruno', 'age': 34, 'active': True}]

Decoded json (simple array):
[{"name": "Ana", "age": null, "active": false}, {"name": "Bruno", "age": 34, "active": true}]

Toon Plus Format (simple object):
{name,age,is_student}
John,30,false

Decoded Dictionary (simple object):
{'name': 'John', 'age': 30, 'is_student': False}

Decoded json (simple object):
{"name": "John", "age": 30, "is_student": false}

=== dict inside dict (named simple object) ===
Users{name,age}
Alice,25

decoded (named simple object): {'Users': {'name': 'Alice', 'age': 25}}

=== list inside dict ===
Users{name,age,jobs}
Alice,25,[Engineer, Writer]

decoded (list inside dict): {'Users': {'name': 'Alice', 'age': 25, 'jobs': ['Engineer', 'Writer']}}

=== dict inside dict inside dict ===
Users{name,age,address}
Alice,25,{city: Wonderland, zip: 12345}

decoded (dict inside dict inside dict): {'Users': {'name': 'Alice', 'age': 25, 'address': {'city': 'Wonderland', 'zip': 12345}}}

=== simple list of numbers ===
[1, 2, 4, 5, 6]

decoded (simple list of numbers): [1, 2, 4, 5, 6]

```

```python
# test performance
import time
from toon_plus import toon_plus

def measure(func, *args, **kwargs):
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    elapsed_ms = (end - start) * 1000  # convertendo para milissegundos
    return result, elapsed_ms

data = """
users{name,age,active,country}
Ana,null,false,Brasil
Bruno,34,true,Portugal

products{id,name,price}
1,Caneta,2.5
2,Caderno,15.0
"""

dict_decoded, t_decode = measure(toon_plus.decode, data)  # function decode
print(f"\nDecoded toon plus [{t_decode:.3f} ms]:")
print(dict_decoded)

data_toon_ = """
users{name,age,active,country}
Ana,null,false,Brasil
Bruno,34,true,Portugal

products{id,name,price}
1,Caneta,2.5
2,Caderno,15.0
"""

toon_to_json, t_json_ = measure(toon_plus.decode2json, data_toon_)  # function decode2json
print(f"\nToon to json [{t_json_:.3f} ms]:")
print(toon_to_json)
```

## Efficiency

Toon Plus is 11% to 21% more efficient than normal toon

