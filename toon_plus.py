import json
import re

class toon_plus:

    # ---------------------------
    # encode helpers
    # ---------------------------
    @staticmethod
    def encode_value(v):
        """Encode Python value without JSON escaping."""
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        if isinstance(v, list):
            return f"[{', '.join(map(toon_plus.encode_value, v))}]"
        if isinstance(v, dict):
            inner = ", ".join(f"{k}: {toon_plus.encode_value(vv)}" for k, vv in v.items())
            return "{" + inner + "}"

        # Security: detect strings that are isolated "true", "false", "none"
        if isinstance(v, str):
            if v.lower() in ("true", "false", "none"):
                raise ValueError(f'Isolated boolean/None strings are not allowed. "{v}"')

        s = str(v)
        if any(c in s for c in [",", "[", "]", "{", "}", "\n", "\r", '"']):
            return '"' + s.replace('"', '\\"') + '"'
        return s

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
            if ch in "[{":
                stack.append(ch)
                continue
            if ch in "]}":
                if stack:
                    stack.pop()
                continue
            if ch == "," and not stack and not in_quotes:
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
            if in_quotes:
                cur.append(ch)
                continue
            if ch in "[{":
                stack.append(ch)
                cur.append(ch)
                continue
            if ch in "]}":
                if stack:
                    stack.pop()
                cur.append(ch)
                continue
            if ch == ":" and not stack and not in_quotes:
                key = "".join(cur).strip()
                val = token[i + 1:].strip()
                return key, val
            cur.append(ch)
        return token.strip(), ""

    # ---------------------------
    # value parser
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

        if tok[0] == '"' and tok[-1] == '"':
            return tok[1:-1].replace('\\"', '"')

        if tok[0] == '[' and tok[-1] == ']':
            inner = tok[1:-1].strip()
            if not inner:
                return []
            return list(map(toon_plus.parse_value, toon_plus._split_top_level_commas(inner)))

        if tok[0] == '{' and tok[-1] == '}':
            inner = tok[1:-1].strip()
            if not inner:
                return {}
            obj = {}
            for p in toon_plus._split_top_level_commas(inner):
                k, v = toon_plus._split_key_value(p)
                obj[k.strip().strip('"')] = toon_plus.parse_value(v)
            return obj

        # números
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
            if all(not isinstance(v, (list, dict)) for v in data.values()):
                keys = list(data.keys())
                header = "{" + ",".join(keys) + "}"
                row = ",".join(cls.encode_value(data[k]) for k in keys)
                return header + "\n" + row

            blocks = []
            for name, value in data.items():
                if isinstance(value, list):
                    blocks.append(cls._encode_list_block(name, value))
                    continue
                if isinstance(value, dict):
                    keys = list(value.keys())
                    row = ",".join(cls.encode_value(value[k]) for k in keys)
                    blocks.append(f"{name}{{{','.join(keys)}}}\n{row}")
                    continue
                raise ValueError(f"Unsupported type inside dict at key '{name}'")
            return "\n\n".join(blocks)
        raise TypeError("Input must be dict or list.")

    @classmethod
    def _encode_list_block(cls, name, items):
        if not items or not isinstance(items[0], dict):
            return f"[{', '.join(map(cls.encode_value, items))}]"

        keys = list(items[0].keys())
        header = f"{name}{{{','.join(keys)}}}" if name else "{" + ",".join(keys) + "}"
        rows = [",".join(map(cls.encode_value, (it[k] for k in keys))) for it in items]
        return header + "\n" + "\n".join(rows)

    # ---------------------------
    # decode main
    # ---------------------------
    @classmethod
    def toonplus_to_dict(cls, text: str):
        text = text.strip()

        # pure list
        if text.startswith("[") and text.endswith("]"):
            return cls.parse_value(text)

        # Find blocks
        header_re = re.compile(r"^([A-Za-z0-9_]+)?\{([^}]+)\}$", re.MULTILINE)
        matches = list(header_re.finditer(text))
        if not matches:
            raise ValueError("Invalid Toon Plus format")

        # Single unnamed block (object or list of objects)
        if len(matches) == 1 and matches[0].group(1) is None:
            m = matches[0]
            keys = [k.strip() for k in m.group(2).split(",")]
            body = text[m.end():].strip()
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            if len(lines) == 1:
                vals = cls._split_top_level_commas(lines[0])
                return dict(zip(keys, map(cls.parse_value, vals)))
            return [dict(zip(keys, map(cls.parse_value, cls._split_top_level_commas(ln)))) for ln in lines]

        # Multiple blocks
        result = {}
        for i, m in enumerate(matches):
            name = m.group(1)
            keys = [k.strip() for k in m.group(2).split(",")]
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            if len(lines) == 1:
                vals = cls._split_top_level_commas(lines[0])
                result[name] = dict(zip(keys, map(cls.parse_value, vals)))
            else:
                result[name] = [dict(zip(keys, map(cls.parse_value, cls._split_top_level_commas(ln)))) for ln in lines]
        return result

    @staticmethod
    def _parse_value_to_json_fast(tok: str):
        tok = tok.strip()
        if not tok:
            return "null"
        low = tok.lower()
        if low in ("null", "none"):
            return "null"
        if low == "true":
            return "true"
        if low == "false":
            return "false"

        # número
        try:
            if '.' in tok:
                float(tok)
            else:
                int(tok)
            return tok
        except ValueError:
            pass

        # string
        if tok[0] == '"' and tok[-1] == '"':
            return '"' + tok[1:-1].replace('\\"', '"') + '"'
        # valores complexos (listas ou objetos)
        if tok[0] == '[' and tok[-1] == ']':
            inner = tok[1:-1].strip()
            if not inner:
                return "[]"
            items = [toon_plus._parse_value_to_json_fast(x) for x in toon_plus._split_top_level_commas(inner)]
            return "[" + ",".join(items) + "]"
        if tok[0] == '{' and tok[-1] == '}':
            inner = tok[1:-1].strip()
            if not inner:
                return "{}"
            parts = []
            for p in toon_plus._split_top_level_commas(inner):
                k, v = toon_plus._split_key_value(p)
                key_clean = k.strip().strip('"')  # remove espaços e aspas externas
                val_json = toon_plus._parse_value_to_json_fast(v)
                parts.append(f'"{key_clean}":{val_json}')
            return "{" + ",".join(parts) + "}"

        # string normal
        return '"' + tok.replace('"', '\\"') + '"'
    
    @classmethod
    def decode2json(cls, text: str):
        text = text.strip()
        if not text:
            return "{}"

        # lista pura
        if text.startswith("[") and text.endswith("]"):
            return cls._parse_value_to_json_fast(text)

        header_re = re.compile(r"^([A-Za-z0-9_]+)?\{([^}]+)\}$", re.MULTILINE)
        matches = list(header_re.finditer(text))
        if not matches:
            raise ValueError("Invalid Toon Plus format")

        # Single unnamed block
        if len(matches) == 1 and matches[0].group(1) is None:
            m = matches[0]
            keys = [k.strip() for k in m.group(2).split(",")]
            body_lines = [l.strip() for l in text[m.end():].splitlines() if l.strip()]
            if len(body_lines) == 1:
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(body_lines[0])]
                items = [f'"{k}":{v}' for k, v in zip(keys, vals)]
                return "{" + ",".join(items) + "}"
            # lista de objetos
            all_items = []
            for ln in body_lines:
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(ln)]
                all_items.append("{" + ",".join(f'"{k}":{v}' for k, v in zip(keys, vals)) + "}")
            return "[" + ",".join(all_items) + "]"

        # múltiplos blocos
        result_parts = []
        for i, m in enumerate(matches):
            name = m.group(1)
            keys = [k.strip() for k in m.group(2).split(",")]
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body_lines = [l.strip() for l in text[start:end].splitlines() if l.strip()]

            if len(body_lines) == 1:
                vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(body_lines[0])]
                items = [f'"{k}":{v}' for k, v in zip(keys, vals)]
                result_parts.append(f'"{name}":{{' + ",".join(items) + "}}")
            else:
                block_items = []
                for ln in body_lines:
                    vals = [cls._parse_value_to_json_fast(v) for v in cls._split_top_level_commas(ln)]
                    block_items.append("{" + ",".join(f'"{k}":{v}' for k, v in zip(keys, vals)) + "}")
                result_parts.append(f'"{name}":[' + ",".join(block_items) + "]")
        return "{" + ",".join(result_parts) + "}"  



    # ---------------------------
    # public methods
    # ---------------------------
    @classmethod
    def encode(cls, data):
        return cls.dict_to_toonplus(data)

    # toon plus to dict
    @classmethod
    def decode(cls, text):
        json_data = cls.decode2json(text)
        return json.loads(json_data)
    
    # toon plus to dict method 2
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
