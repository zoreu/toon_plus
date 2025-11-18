import json
import re


class toon_plus:
    # ---------------------------
    # encode / decode helpers
    # ---------------------------
    @staticmethod
    def encode_value(v):
        """Encode Python value WITHOUT using JSON (no backslashes)."""
        # null
        if v is None:
            return "null"

        # bool
        if isinstance(v, bool):
            return "true" if v else "false"

        # number
        if isinstance(v, (int, float)):
            return str(v)

        # list → [a, b, c]
        if isinstance(v, list):
            inner = ", ".join(toon_plus.encode_value(x) for x in v)
            return f"[{inner}]"

        # dict → {k: v, k2: v2}
        if isinstance(v, dict):
            inner = ", ".join(f"{k}: {toon_plus.encode_value(vv)}" for k, vv in v.items())
            return f"{{{inner}}}"

        # strings normais → só colocar aspas se necessário
        s = str(v)
        if any(c in s for c in [",", "[", "]", "{", "}", "\n", "\r", '"']):
            # usar concatenação para evitar confusão com escapes em f-strings
            return '"' + s.replace('"', '\\"') + '"'
        return s

    # ---------------------------
    # parsing helpers (robustos)
    # ---------------------------
    @staticmethod
    def _split_top_level_commas(text: str):
        """
        Split a string by commas at top level — ignore commas inside quotes, [] or {}.
        Returns list of tokens (raw, not stripped).
        """
        parts = []
        cur = []
        stack = []  # will store opening brackets: '[' or '{'
        in_quotes = False
        esc = False
        for ch in text:
            if esc:
                cur.append(ch)
                esc = False
                continue

            if ch == "\\":
                # treat escape char, keep backslash and set escape to attach next char
                cur.append(ch)
                esc = True
                continue

            if ch == '"' and not esc:
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

            if ch in "]}" and stack:
                stack.pop()
                cur.append(ch)
                continue

            if ch == "," and not stack and not in_quotes:
                parts.append("".join(cur).strip())
                cur = []
                continue

            cur.append(ch)

        # last token
        if cur:
            parts.append("".join(cur).strip())
        return parts

    @staticmethod
    def _split_key_value(token: str):
        """
        Split a token like "k: v" into (k, v) at the top-level colon.
        Will ignore colons inside quotes or nested brackets.
        """
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
            if ch == '"' and not esc:
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
            if ch in "]}" and stack:
                stack.pop()
                cur.append(ch)
                continue
            if ch == ":" and not stack and not in_quotes:
                # split here
                key = "".join(cur).strip()
                val = token[i + 1 :].strip()
                return key, val
            cur.append(ch)
        # no colon found at top level
        return token.strip(), ""

    @staticmethod
    def _strip_wrapping_quotes(s: str):
        s = s.strip()
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"' and not s.endswith('\\"'):
            return s[1:-1].replace('\\"', '"')
        return s

    # ---------------------------
    # parse scalar/list/dict tokens
    # ---------------------------
    @staticmethod
    def parse_value(tok: str):
        """Parse Toon Plus token back to Python value (supports [..] and {..})."""
        if tok is None:
            return None
        tok = tok.strip()
        if tok == "":
            return ""

        low = tok.lower()
        if low in ("null", "none"):
            return None
        if low == "true":
            return True
        if low == "false":
            return False

        # numbers
        if re.fullmatch(r"-?\d+", tok):
            return int(tok)
        if re.fullmatch(r"-?\d+\.\d+", tok):
            return float(tok)

        # quoted string
        if tok.startswith('"') and tok.endswith('"'):
            return toon_plus._strip_wrapping_quotes(tok)

        # list: [ ... ]
        if tok.startswith("[") and tok.endswith("]"):
            inner = tok[1:-1].strip()
            if inner == "":
                return []
            parts = toon_plus._split_top_level_commas(inner)
            return [toon_plus.parse_value(p) for p in parts]

        # dict: { ... }
        if tok.startswith("{") and tok.endswith("}"):
            inner = tok[1:-1].strip()
            if inner == "":
                return {}
            parts = toon_plus._split_top_level_commas(inner)
            obj = {}
            for p in parts:
                k, v = toon_plus._split_key_value(p)
                k = k.strip()
                # try to strip quotes around keys if present
                if k.startswith('"') and k.endswith('"'):
                    k = toon_plus._strip_wrapping_quotes(k)
                obj[k] = toon_plus.parse_value(v.strip())
            return obj

        # fallback: plain string
        return tok

    # ---------------------------
    # encoding: python -> toon plus
    # ---------------------------
    @classmethod
    def dict_to_toonplus(cls, data):
        """Main encoder. Supports lists, named-blocks, simple objects and nested lists/dicts encoded as plain-looking tokens."""
        # anonymous list
        if isinstance(data, list):
            return cls._encode_list_block(None, data)

        # top-level simple dict: all scalars -> {k1,k2}
        if isinstance(data, dict):
            is_all_scalars = all(not isinstance(v, (list, dict)) for v in data.values())
            if is_all_scalars:
                keys = list(data.keys())
                header = "{" + ",".join(keys) + "}"
                row = ",".join(cls.encode_value(data[k]) for k in keys)
                return header + "\n" + row

            # otherwise expect dict of name->list or name->dict (possibly nested)
            blocks = []
            for name, value in data.items():
                if isinstance(value, list):
                    blocks.append(cls._encode_list_block(name, value))
                    continue
                if isinstance(value, dict):
                    # encode dict as named object block (may contain nested list/dict tokens)
                    keys = list(value.keys())
                    header = f"{name}" + "{" + ",".join(keys) + "}"
                    row = ",".join(cls.encode_value(value[k]) for k in keys)
                    blocks.append(header + "\n" + row)
                    continue
                raise ValueError(f"Invalid value at '{name}' (must be list or dict).")
            return "\n\n".join(blocks)

        raise TypeError("Input must be a dict or list.")

    @classmethod
    def _encode_list_block(cls, name, items):
        """Encode a block (named or anonymous) for a list of dicts."""
        if not items:
            return f"{name}[]" if name else "[]"

        keys = list(items[0].keys())
        for it in items:
            if set(it.keys()) != set(keys):
                raise ValueError("All items in the list must have the same keys (same set).")

        header = f"{name}{{{','.join(keys)}}}" if name else "{" + ",".join(keys) + "}"
        rows = []
        for it in items:
            rows.append(",".join(cls.encode_value(it[k]) for k in keys))
        return header + "\n" + "\n".join(rows)

    # ---------------------------
    # decoding: toon plus -> python
    # ---------------------------
    @classmethod
    def toonplus_to_dict(cls, text: str):
        if text is None:
            return None
        txt = text.strip()
        if not txt:
            return {}

        # header must be alone on its line (like Name{...} or {...})
        header_pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)?([\[\{])([^}\]]+)([\]\}])\s*$")
        matches = list(header_pattern.finditer(txt))
        if not matches:
            raise ValueError("Invalid Toon Plus format: no header found.")

        result = {}
        unnamed = None

        for i, m in enumerate(matches):
            name_group = m.group(1)
            opener = m.group(2)  # '[' or '{'
            keys_raw = m.group(3)
            keys = [k.strip() for k in keys_raw.split(",") if k.strip()]

            start_body = m.end()
            end_body = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
            body = txt[start_body:end_body].strip()
            lines = [ln for ln in (l.strip() for l in body.splitlines()) if ln != ""]

            if opener == "{":
                # if multiple lines -> list of objects
                if len(lines) > 1:
                    records = []
                    for ln in lines:
                        vals = cls._split_top_level_commas(ln)
                        parsed_vals = list(map(cls.parse_value, vals))
                        records.append(dict(zip(keys, parsed_vals)))
                    if name_group:
                        result[name_group] = records
                    else:
                        unnamed = records
                else:
                    # single line -> object
                    if lines:
                        vals = cls._split_top_level_commas(lines[0])
                        parsed_vals = list(map(cls.parse_value, vals))
                        obj = dict(zip(keys, parsed_vals))
                    else:
                        obj = {k: None for k in keys}
                    if name_group:
                        result[name_group] = obj
                    else:
                        unnamed = obj
                continue

            # opener == '[' (legacy) treat similar to list block
            records = []
            for ln in lines:
                vals = cls._split_top_level_commas(ln)
                parsed_vals = list(map(cls.parse_value, vals))
                records.append(dict(zip(keys, parsed_vals)))
            if name_group:
                result[name_group] = records
            else:
                unnamed = records

        return result if result else unnamed

    # convenience wrappers
    @classmethod
    def encode(cls, data):
        return cls.dict_to_toonplus(data)

    @classmethod
    def decode(cls, text):
        return cls.toonplus_to_dict(text)

    @classmethod
    def decode2json(cls, text):
        return json.dumps(cls.toonplus_to_dict(text), ensure_ascii=False)

    
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
