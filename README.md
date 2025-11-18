# toon_plus
Toon Plus format implementation based on Toon + CSV.

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
```
```bash
# OUTPUT

Toon Plus Format:
users[name,age,active,country]
Ana,null,false,Brasil
Bruno,34,true,Portugal

products[id,name,price]
1,Caneta,2.5
2,Caderno,15.0

Decoded Dictionary:
{'users': [{'name': 'Ana', 'age': None, 'active': False, 'country': 'Brasil'}, {'name': 'Bruno', 'age': 34, 'active': True, 'country': 'Portugal'}], 'products': [{'id': 1, 'name': 'Caneta', 'price': 2.5}, {'id': 2, 'name': 
'Caderno', 'price': 15.0}]}

Decoded json:
{"users": [{"name": "Ana", "age": null, "active": false, "country": "Brasil"}, {"name": "Bruno", "age": 34, "active": true, "country": "Portugal"}], "products": [{"id": 1, "name": "Caneta", "price": 2.5}, {"id": 2, "name": 
"Caderno", "price": 15.0}]}

Toon Plus Format (simple array):
[name,age,active]
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
```

