import json
import re


class toon_plus:
    # ---------------------------
    # encode / decode helpers
    # ---------------------------
    @staticmethod
    def encode_value(v):
        """Encode Python scalar to toon plus token"""
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        s = str(v)
        # escape quotes if present, and quote if contains comma or brackets or braces or newline
        if any(c in s for c in [",", "[", "]", "{", "}", "\n", "\r"]):
            return '"' + s.replace('"', '\\"') + '"'
        return s

    @staticmethod
    def parse_value(tok: str):
        """Parse a single token (string) into python value"""
        tok = tok.strip()
        if not tok:
            return ""
        low = tok.lower()
        if low in ("null", "none"):
            return None
        if low == "true":
            return True
        if low == "false":
            return False

        # quoted string?
        if tok.startswith('"') and tok.endswith('"'):
            inner = tok[1:-1].replace('\\"', '"')
            return inner

        # try numbers
        if re.fullmatch(r"-?\d+", tok):
            return int(tok)
        if re.fullmatch(r"-?\d+\.\d+", tok):
            return float(tok)

        return tok

    # ---------------------------
    # encoding: python -> toon plus
    # ---------------------------
    @classmethod
    def dict_to_toonplus(cls, data):
        """Main encoder. Supports:
           - dict of named-lists (blocks)
           - list (anonymous list)
           - simple dict (object) -> encoded with {keys} header
        """
        # anonymous list
        if isinstance(data, list):
            return cls._encode_list_block(None, data)

        # simple dict with only scalar values -> use {k1,k2} style (object)
        if isinstance(data, dict):
            is_all_scalars = all(not isinstance(v, (list, dict)) for v in data.values())
            if is_all_scalars:
                keys = list(data.keys())
                header = "{" + ",".join(keys) + "}"
                row = ",".join(cls.encode_value(data[k]) for k in keys)
                return header + "\n" + row

            # otherwise expect dict where values are lists (named blocks)
            blocks = []
            for name, value in data.items():
                if not isinstance(value, list):
                    raise ValueError(f"The value of '{name}' must be a list when the dict is not a simple object.")
                blocks.append(cls._encode_list_block(name, value))
            return "\n\n".join(blocks)

        raise TypeError("Input must be a dict or list.")

    @classmethod
    def _encode_list_block(cls, name, items):
        """Encode a block (named or anonymous) for a list of dicts."""
        if not items:
            # empty list: header with empty keys
            if name:
                return f"{name}[]"
            return "[]"

        # ensure uniform keys
        keys = list(items[0].keys())
        for it in items:
            if set(it.keys()) != set(keys):
                raise ValueError("All items in the list must have the same keys (same set).")

        if name:
            header = f"{name}[{','.join(keys)}]"
        else:
            header = f"[{','.join(keys)}]"

        rows = []
        for it in items:
            rows.append(",".join(cls.encode_value(it[k]) for k in keys))

        return header + "\n" + "\n".join(rows)

    # ---------------------------
    # decoding: toon plus -> python
    # ---------------------------
    @classmethod
    def toonplus_to_dict(cls, text: str):
        """Parse a toon plus text into python structures.

        Recognized header forms (must be at start of a line):
          - name[key1,key2]         -> named list block
          - [key1,key2]             -> anonymous list block
          - {key1,key2}             -> simple object (one row -> dict)
        Headers have no trailing colon (per your examples).
        """
        if text is None:
            return None
        txt = text.strip()
        if not txt:
            return {}

        # find header lines and their positions
        header_pattern = re.compile(r"(?m)^([A-Za-z0-9_]+)?([\[\{])([^]\}]+)([\]\}])\s*$")
        matches = list(header_pattern.finditer(txt))
        if not matches:
            raise ValueError("Invalid Toon Plus format: no header found.")

        result = {}
        unnamed_result = None

        for i, m in enumerate(matches):
            # header info
            name_group = m.group(1)  # may be None
            opener = m.group(2)      # '[' or '{'
            keys_raw = m.group(3)    # 'k1,k2,...'
            closer = m.group(4)      # ']' or '}'

            keys = [k.strip() for k in keys_raw.split(",") if k.strip()]

            start_body = m.end() + 1  # move to line after header; +1 to skip newline
            # determine end: start of next match or end of text
            end_body = matches[i + 1].start() if i + 1 < len(matches) else len(txt)

            body = txt[m.end():end_body].strip("\n\r ")

            # split non-empty lines
            lines = [ln for ln in (l.strip() for l in body.splitlines()) if ln != ""]

            # if opener is '{' treat as simple object: expect exactly one line of values
            if opener == "{":
                if not lines:
                    # empty object -> map keys to None?
                    obj = {k: None for k in keys}
                else:
                    # take first non-empty line
                    vals = cls._split_line_preserving_quotes(lines[0])
                    if len(vals) != len(keys):
                        raise ValueError("Number of values does not match keys in object.")
                    obj = dict(zip(keys, map(cls.parse_value, vals)))

                # if named (name_group present) we put under that name as object, else return object directly
                if name_group:
                    result[name_group] = obj
                else:
                    unnamed_result = obj
                continue

            # else opener == '[' -> list block
            if not lines:
                records = []
            else:
                records = []
                for ln in lines:
                    vals = cls._split_line_preserving_quotes(ln)
                    if len(vals) != len(keys):
                        raise ValueError("Number of values does not match keys in list block.")
                    records.append(dict(zip(keys, map(cls.parse_value, vals))))

            if name_group:
                result[name_group] = records
            else:
                unnamed_result = records

        # if only unnamed block exists, return it directly
        if not result and unnamed_result is not None:
            return unnamed_result

        return result

    @staticmethod
    def _split_line_preserving_quotes(line: str):
        """Split CSV-like line by commas but preserve quoted tokens.
        Accepts double-quoted tokens with \" escaping.
        """
        parts = []
        cur = []
        in_quotes = False
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '"' and (i == 0 or line[i - 1] != "\\"):
                in_quotes = not in_quotes
                cur.append(ch)
            elif ch == "," and not in_quotes:
                token = "".join(cur).strip()
                parts.append(token)
                cur = []
            else:
                cur.append(ch)
            i += 1
        token = "".join(cur).strip()
        if token != "":
            parts.append(token)
        return parts

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
