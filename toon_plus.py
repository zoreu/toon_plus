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
            inner = ", ".join(toon_plus.encode_value(x) for x in v)
            return f"[{inner}]"

        if isinstance(v, dict):
            inner = ", ".join(
                f"{k}: {toon_plus.encode_value(vv)}"
                for k, vv in v.items()
            )
            return "{" + inner + "}"

        s = str(v)

        # If the string contains special characters, enclose it in quotation marks.
        if any(c in s for c in [",", "[", "]", "{", "}", "\n", "\r", '"']):
            return '"' + s.replace('"', '\\"') + '"'

        return s

    # ---------------------------
    # split helpers
    # ---------------------------
    @staticmethod
    def _split_top_level_commas(text: str):
        parts = []
        cur = []
        stack = []
        in_quotes = False
        esc = False

        for ch in text:
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

            if ch == "," and not stack and not in_quotes:
                parts.append("".join(cur).strip())
                cur = []
                continue

            cur.append(ch)

        if cur:
            parts.append("".join(cur).strip())

        return parts

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

        if tok.lower() in ("null", "none"):
            return None

        if tok.lower() == "true":
            return True

        if tok.lower() == "false":
            return False

        if re.fullmatch(r"-?\d+", tok):
            return int(tok)

        if re.fullmatch(r"-?\d+\.\d+", tok):
            return float(tok)

        if tok.startswith('"') and tok.endswith('"'):
            return tok[1:-1].replace('\\"', '"')

        if tok.startswith("[") and tok.endswith("]"):
            inner = tok[1:-1].strip()
            if not inner:
                return []
            parts = toon_plus._split_top_level_commas(inner)
            return [toon_plus.parse_value(p) for p in parts]

        if tok.startswith("{") and tok.endswith("}"):
            inner = tok[1:-1].strip()
            if not inner:
                return {}
            parts = toon_plus._split_top_level_commas(inner)
            obj = {}
            for p in parts:
                k, v = toon_plus._split_key_value(p)
                k = k.strip().strip('"')
                obj[k] = toon_plus.parse_value(v)
            return obj

        return tok

    # ---------------------------
    # encode main
    # ---------------------------
    @classmethod
    def dict_to_toonplus(cls, data):
        # LIST at the top
        if isinstance(data, list):
            return cls._encode_list_block(None, data)

        # DICTIONARY at the top
        if isinstance(data, dict):

            # ✔️ CASE 1 — simple dictionary (only scalars)
            if all(not isinstance(v, (list, dict)) for v in data.values()):
                keys = list(data.keys())
                header = "{" + ",".join(keys) + "}"
                row = ",".join(cls.encode_value(data[k]) for k in keys)
                return header + "\n" + row

            # ✔️ CASE 2 — dict containing lists or other dicts
            blocks = []

            for name, value in data.items():

                # simple list or list of objects
                if isinstance(value, list):
                    blocks.append(cls._encode_list_block(name, value))
                    continue

                # simple dictionary
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
        # simple list
        if not items or not isinstance(items[0], dict):
            encoded = ", ".join(cls.encode_value(x) for x in items)
            return f"[{encoded}]"

        # list of objects
        keys = list(items[0].keys())
        header = f"{name}{{{','.join(keys)}}}" if name else "{" + ",".join(keys) + "}"

        rows = []
        for it in items:
            rows.append(",".join(cls.encode_value(it[k]) for k in keys))

        return header + "\n" + "\n".join(rows)

    # ---------------------------
    # decode main
    # ---------------------------
    @classmethod
    def toonplus_to_dict(cls, text: str):
        text = text.strip()

        # Pure list format
        if text.startswith("[") and text.endswith("]"):
            return cls.parse_value(text)

        # Find blocks
        header_re = re.compile(r"^([A-Za-z0-9_]+)?\{([^}]+)\}$", re.MULTILINE)
        matches = list(header_re.finditer(text))

        if not matches:
            raise ValueError("Invalid Toon Plus format")

        # Single unnamed block
        if len(matches) == 1 and matches[0].group(1) is None:
            m = matches[0]
            keys = [k.strip() for k in m.group(2).split(",")]
            body = text[m.end():].strip()
            lines = [l.strip() for l in body.split("\n") if l.strip()]

            if len(lines) == 1:
                vals = cls._split_top_level_commas(lines[0])
                vals = [cls.parse_value(v) for v in vals]
                return dict(zip(keys, vals))  # <-- aqui retorna dict diretamente
            else:
                arr = []
                for ln in lines:
                    vals = cls._split_top_level_commas(ln)
                    vals = [cls.parse_value(v) for v in vals]
                    arr.append(dict(zip(keys, vals)))
                return arr

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
                vals = [cls.parse_value(v) for v in vals]
                result[name] = dict(zip(keys, vals))
                continue

            arr = []
            for ln in lines:
                vals = cls._split_top_level_commas(ln)
                vals = [cls.parse_value(v) for v in vals]
                arr.append(dict(zip(keys, vals)))

            result[name] = arr

        return result



    @classmethod
    def encode(cls, data):
        return cls.dict_to_toonplus(data)

    @classmethod
    def decode(cls, text):
        return cls.toonplus_to_dict(text)

    @classmethod
    def decode2json(cls, text):
        return json.dumps(cls.decode(text), ensure_ascii=False)

    
if __name__ == "__main__":
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
