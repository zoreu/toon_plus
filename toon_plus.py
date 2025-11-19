import json
import re

class toon_plus:

    # ---------------------------
    # encode helpers
    # ---------------------------
    @staticmethod
    def encode_value(v):
        """Encode Python value without JSON escaping, preserving string types correctly."""
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        
        # Se for número real (int/float), retorna string sem aspas
        if isinstance(v, (int, float)):
            return str(v)
        
        if isinstance(v, list):
            # Encode recursivo para listas
            return f"[{', '.join(map(toon_plus.encode_value, v))}]"
        
        if isinstance(v, dict):
            # Encode recursivo para dicts inline
            inner = ", ".join(f"{k}: {toon_plus.encode_value(vv)}" for k, vv in v.items())
            return "{" + inner + "}"

        if isinstance(v, str):
            # Security: detect strings that are isolated "true", "false", "none"
            if v.lower() in ("true", "false", "none", "null"):
                raise ValueError(f'Isolated boolean/None strings are not allowed. "{v}"')
            
            # FIX 1: Detect strings that look exactly like numbers and force quotes.
            # This ensures "40" stays "40" (string) and doesn't become 40 (int) on decode.
            # Covers integers and floats like "10.5"
            if re.fullmatch(r"-?\d+(\.\d+)?", v):
                return '"' + v + '"'

            s = str(v)
            # Quote if special chars exist or just to be safe
            if any(c in s for c in [",", "[", "]", "{", "}", "\n", "\r", '"']):
                return '"' + s.replace('"', '\\"') + '"'
            return s

        # Fallback
        s = str(v)
        return '"' + s.replace('"', '\\"') + '"'

    # ---------------------------
    # split helpers
    # ---------------------------
    @staticmethod
    def _split_top_level_commas(text: str):
        stack = []
        in_quotes = False
        esc = False
        start = 0

        for i, ch in enumerate(text):
            if esc:
                esc = False
                continue
            if ch == '\\':
                esc = True
                continue
            if ch == '"':
                in_quotes = not in_quotes
                continue
            if not in_quotes:
                if ch in "[{":
                    stack.append(ch)
                elif ch in "]}":
                    if stack:
                        stack.pop()
                elif ch == "," and not stack:
                    yield text[start:i].strip()
                    start = i + 1
        
        if start < len(text):
            yield text[start:].strip()

    @staticmethod
    def _split_key_value(token: str):
        cur = []
        stack = []
        in_quotes = False
        esc = False

        for i, ch in enumerate(token):
            if esc:
                cur.append(ch)
                esc = False
                continue
            if ch == "\\":
                cur.append(ch)
                esc = True
                continue
            if ch == '"':
                in_quotes = not in_quotes
                cur.append(ch)
                continue
            if not in_quotes:
                if ch in "[{":
                    stack.append(ch)
                elif ch in "]}":
                    if stack:
                        stack.pop()
                elif ch == ":" and not stack:
                    key = "".join(cur).strip()
                    val = token[i + 1:].strip()
                    return key, val
            cur.append(ch)
        return token.strip(), ""

    # ---------------------------
    # value parser (Direct Dict)
    # ---------------------------
    @staticmethod
    def parse_value(tok: str):
        tok = tok.strip()
        if not tok:
            return None

        low = tok.lower()
        if low in ("null", "none"):
            return None
        if low == "true":
            return True
        if low == "false":
            return False

        # Strings explícitas (com aspas)
        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1].replace('\\"', '"')

        # Listas
        if tok.startswith('[') and tok.endswith(']'):
            inner = tok[1:-1].strip()
            if not inner:
                return []
            return list(map(toon_plus.parse_value, toon_plus._split_top_level_commas(inner)))

        # Objetos
        if tok.startswith('{') and tok.endswith('}'):
            inner = tok[1:-1].strip()
            if not inner:
                return {}
            obj = {}
            for p in toon_plus._split_top_level_commas(inner):
                k, v = toon_plus._split_key_value(p)
                obj[k.strip().strip('"')] = toon_plus.parse_value(v)
            return obj

        # Números (apenas se NÃO tiver aspas)
        if re.fullmatch(r"-?\d+", tok):
            return int(tok)
        if re.fullmatch(r"-?\d+\.\d+", tok):
            return float(tok)

        return tok

    # ---------------------------
    # encode main
    # ---------------------------
    @classmethod
    def dict_to_toonplus(cls, data):
        if isinstance(data, list):
            return cls._encode_list_block(None, data)

        if isinstance(data, dict):
            # FIX 2: Melhor detecção de "Complexidade".
            # Um dicionário só precisa ser dividido em blocos se contiver:
            # 1. Outro Dicionário (Nested Object)
            # 2. Uma Lista de Dicionários (List of Objects)
            # Se tiver apenas primitivos OU listas de primitivos, ele é "Flat" e pode ser uma única linha.
            
            has_complex_values = False
            for v in data.values():
                if isinstance(v, dict):
                    has_complex_values = True
                    break
                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                    has_complex_values = True
                    break
            
            # Se for simples (incluindo listas de números/strings), codifica como bloco único {header}\nRow
            if not has_complex_values:
                keys = list(data.keys())
                header = "{" + ",".join(keys) + "}"
                row = ",".join(cls.encode_value(data[k]) for k in keys)
                return header + "\n" + row

            # Se tiver valores complexos, separamos em blocos
            blocks = []
            for name, value in data.items():
                # Lista de objetos -> Novo bloco
                if isinstance(value, list):
                    # Se for lista de primitivos, poderia ter sido pega acima, mas se estamos aqui
                    # é porque o dict é misto. ToonPlus não lida bem com raízes mistas sem nome.
                    # Mas vamos verificar:
                    if value and not isinstance(value[0], dict):
                         # Lista de primitivos em um dict complexo? 
                         # Idealmente isso seria suportado, mas na estrutura de blocos
                         # o formato geralmente espera Nome{Header}.
                         # Vamos forçar encode_list_block que lida com isso.
                         pass
                    blocks.append(cls._encode_list_block(name, value))
                    continue
                
                # Dicionário aninhado -> Novo bloco
                if isinstance(value, dict):
                    keys = list(value.keys())
                    row = ",".join(cls.encode_value(value[k]) for k in keys)
                    blocks.append(f"{name}{{{','.join(keys)}}}\n{row}")
                    continue
                
                # Primitivo solto em dict complexo (Ex: {"versao": 1, "Users": [...]})
                # Isso ainda geraria erro na spec atual, mas o caso do erro data10 foi resolvido pelo `if not has_complex_values`.
                raise ValueError(f"Unsupported top-level mix for key '{name}'. ToonPlus prefers blocks.")
            return "\n\n".join(blocks)
        
        raise TypeError("Input must be dict or list.")

    @classmethod
    def _encode_list_block(cls, name, items):
        if not items:
            return f"{name}{{}}" if name else "{}"
        
        # Se os itens NÃO forem dicionários (ex: lista de strings), encoda como array inline
        if not isinstance(items[0], dict):
            val = f"[{', '.join(map(cls.encode_value, items))}]"
            return f"{name}{val}" if name else val

        keys = list(items[0].keys())
        header = f"{name}{{{','.join(keys)}}}" if name else "{" + ",".join(keys) + "}"
        rows = [",".join(map(cls.encode_value, (it[k] for k in keys))) for it in items]
        return header + "\n" + "\n".join(rows)

    # ---------------------------
    # decode main (Direct Dict)
    # ---------------------------
    @classmethod
    def toonplus_to_dict(cls, text: str):
        text = text.strip()
        # Lista pura ou valor único
        if text.startswith("[") and text.endswith("]"):
            return cls.parse_value(text)

        header_re = re.compile(r"^([A-Za-z0-9_]+)?\{([^}]+)\}$", re.MULTILINE)
        matches = list(header_re.finditer(text))
        
        if not matches:
            try:
                val = cls.parse_value(text)
                if val is not None: return val
            except:
                pass
            raise ValueError("Invalid Toon Plus format")

        # Bloco Único
        if len(matches) == 1 and matches[0].group(1) is None:
            m = matches[0]
            keys = [k.strip() for k in m.group(2).split(",")]
            body = text[m.end():].strip()
            lines = [l.strip() for l in body.splitlines() if l.strip()]
            
            if len(lines) == 1:
                vals = cls._split_top_level_commas(lines[0])
                return dict(zip(keys, map(cls.parse_value, vals)))
            return [dict(zip(keys, map(cls.parse_value, cls._split_top_level_commas(ln)))) for ln in lines]

        # Múltiplos Blocos ou Bloco Nomeado
        result = {}
        for i, m in enumerate(matches):
            name = m.group(1)
            keys = [k.strip() for k in m.group(2).split(",")]
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            lines = [l.strip() for l in body.splitlines() if l.strip()]
            
            if len(lines) == 1:
                vals = cls._split_top_level_commas(lines[0])
                result[name] = dict(zip(keys, map(cls.parse_value, vals)))
            else:
                result[name] = [dict(zip(keys, map(cls.parse_value, cls._split_top_level_commas(ln)))) for ln in lines]
        return result

    # ---------------------------
    # JSON Converter Helpers
    # ---------------------------
    @staticmethod
    def _parse_value_to_json_fast(tok: str):
        tok = tok.strip()
        if not tok: return "null"
        low = tok.lower()
        if low in ("null", "none"): return "null"
        if low == "true": return "true"
        if low == "false": return "false"

        # String já cotada (ex: "Alice" ou "40")
        if tok.startswith('"') and tok.endswith('"'):
            return tok

        # Complex: List
        if tok.startswith('[') and tok.endswith(']'):
            inner = tok[1:-1].strip()
            if not inner: return "[]"
            items = [toon_plus._parse_value_to_json_fast(x) for x in toon_plus._split_top_level_commas(inner)]
            return "[" + ",".join(items) + "]"
        
        # Complex: Dict
        if tok.startswith('{') and tok.endswith('}'):
            inner = tok[1:-1].strip()
            if not inner: return "{}"
            parts = []
            for p in toon_plus._split_top_level_commas(inner):
                k, v = toon_plus._split_key_value(p)
                key_clean = k.strip().strip('"')
                val_json = toon_plus._parse_value_to_json_fast(v)
                parts.append(f'"{key_clean}":{val_json}')
            return "{" + ",".join(parts) + "}"

        # Number (only if unquoted in file)
        try:
            if '.' in tok: float(tok)
            else: int(tok)
            return tok
        except ValueError:
            pass

        # Fallback string
        return '"' + tok.replace('"', '\\"') + '"'
    
    @classmethod
    def decode2json(cls, text: str):
        text = text.strip()
        if not text: return "{}"

        if text.startswith("[") and text.endswith("]"):
            return cls._parse_value_to_json_fast(text)

        header_re = re.compile(r"^([A-Za-z0-9_]+)?\{([^}]+)\}$", re.MULTILINE)
        matches = list(header_re.finditer(text))
        
        if not matches:
             val = cls._parse_value_to_json_fast(text)
             if val != "null": return val
             raise ValueError("Invalid Toon Plus format")

        # Single unnamed block handling
        if len(matches) == 1 and matches[0].group(1) is None:
            m = matches[0]
            keys = [k.strip() for k in m.group(2).split(",")]
            body_lines = [l.strip() for l in text[m.end():].splitlines() if l.strip()]
            
            if len(body_lines) == 1:
                # Single object
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(body_lines[0])]
                items = [f'"{k}":{v}' for k, v in zip(keys, vals)]
                return "{" + ",".join(items) + "}"
            
            # List of objects
            all_items = []
            for ln in body_lines:
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(ln)]
                all_items.append("{" + ",".join(f'"{k}":{v}' for k, v in zip(keys, vals)) + "}")
            return "[" + ",".join(all_items) + "]"

        # Multiple blocks or Single Named block
        result_parts = []
        for i, m in enumerate(matches):
            name = m.group(1)
            raw_keys = m.group(2).strip()
            keys = [k.strip() for k in raw_keys.split(",")] if raw_keys else []
            
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            body_block = text[start:end].strip()
            body_lines = [l.strip() for l in body_block.splitlines() if l.strip()]

            if len(body_lines) == 1:
                # Treat as Single Dict inside the main Dict
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(body_lines[0])]
                items = [f'"{k}":{v}' for k, v in zip(keys, vals)]
                json_obj = "{" + ",".join(items) + "}"
                result_parts.append(f'"{name}":{json_obj}')
            else:
                # Treat as List of Dicts
                block_items = []
                for ln in body_lines:
                    vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(ln)]
                    block_items.append("{" + ",".join(f'"{k}":{v}' for k, v in zip(keys, vals)) + "}")
                json_arr = "[" + ",".join(block_items) + "]"
                result_parts.append(f'"{name}":{json_arr}')

        return "{" + ",".join(result_parts) + "}"

    # ---------------------------
    # public methods
    # ---------------------------
    @classmethod
    def encode(cls, data):
        return cls.dict_to_toonplus(data)

    @classmethod
    def decode(cls, text):
        return json.loads(cls.decode2json(text))
    
    @classmethod
    def decode2(cls, text):
        return cls.toonplus_to_dict(text)    
    
    @classmethod
    def decode_json(cls, text):
        return json.loads(text)


if __name__ == "__main__":
    data = {
        "users": [
            {"name": "Ana", "age": None, "active": False, "country": "Brasil"},
            {"name": "Bruno", "age": 34, "active": True, "country": "Portugal"}
        ],
        "products": [
            {"id": 1, "name": "Caneta", "price": 2.5},
            {"id": 2, "name": "Caderno", "price": 15.0}
        ]
    }

    data2 = [
        {"name": "Ana", "age": None, "active": False},
        {"name": "Bruno", "age": 34, "active": True}
    ]

    data3 = {'name': 'John', 'age': 30, 'is_student': False}
    data4 = {"Users": {"name": "Alice", "age": 25}}
    data5 = {"Users": {"name": "Alice", "age": 25, "jobs": ['Engineer', 'Writer']}}
    data6 = {"Users": {"name": "Alice", "age": 25, "address": {"city": "Wonderland", "zip": "12345"}}}
    data7 = [1, 2, 4, 5, 6]
    data8 = {"name": "example", "url": True}
    data9 = {"name": "number_string", "value": "12345"}
    data10 = {"name": "Pedro", "numbers": ["10", "20", "30"]}
    data11 = {"nome": "Alice", "numbers": [10,20,30]}
    data12 = {"nome": "Alice", "values": [None, True, False, "text", 42, 3.14, "5.5"]}

    toon_text = toon_plus.encode(data)
    print("Toon Plus Format:")
    print(toon_text)
    print("\nDecoded Dictionary:")
    print(toon_plus.decode(toon_text))
    print("\nDecoded json:")
    print(toon_plus.decode2json(toon_text))

    toon_text2 = toon_plus.encode(data2)
    print("\nToon Plus Format (simple array):")
    print(toon_text2)
    print("\nDecoded Dictionary (simple array):")
    print(toon_plus.decode(toon_text2))
    print("\nDecoded json (simple array):")
    print(toon_plus.decode2json(toon_text2))

    toon_text3 = toon_plus.encode(data3)
    print("\nToon Plus Format (simple object):")
    print(toon_text3)
    print("\nDecoded Dictionary (simple object):")
    print(toon_plus.decode(toon_text3))
    print("\nDecoded json (simple object):")
    print(toon_plus.decode2json(toon_text3))

    print("\n=== dict inside dict ===")
    dict_in_dict = toon_plus.encode(data4)
    print(dict_in_dict)
    print("\ndecoded:", toon_plus.decode(dict_in_dict))

    print("\n=== list inside dict ===")
    list_in_dict = toon_plus.encode(data5)
    print(list_in_dict)
    print("\ndecoded:", toon_plus.decode(list_in_dict))

    print("\n=== dict inside dict inside dict ===")
    dict_in_dict_in_dict = toon_plus.encode(data6)
    print(dict_in_dict_in_dict)
    print("\ndecoded:", toon_plus.decode(dict_in_dict_in_dict))

    print("\n=== simple list of numbers ===")
    list_numbers = toon_plus.encode(data7)
    print(list_numbers)
    print("\ndecoded:", toon_plus.decode(list_numbers))

    print("\n=== string with special characters ===")
    special_string = toon_plus.encode(data8)
    print(special_string)
    print("\ndecoded:", toon_plus.decode(special_string))

    print("\n=== string that looks like a number ===")
    string_number = toon_plus.encode(data9)
    print(string_number)
    print("\ndecoded:", toon_plus.decode(string_number))

    print("\n=== list of number-strings ===")
    list_number_strings = toon_plus.encode(data10)
    print(list_number_strings)
    print("\ndecoded:", toon_plus.decode(list_number_strings))

    print("\n=== list of numbers 2 ===")
    list_numbers_2 = toon_plus.encode(data11)
    print(list_numbers_2)
    print("\ndecoded:", toon_plus.decode(list_numbers_2))

    print("\n=== mixed list ===")
    mixed_list = toon_plus.encode(data12)
    print(mixed_list)
    print("\ndecoded:", toon_plus.decode(mixed_list))
