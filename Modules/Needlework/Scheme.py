class Scheme:
    def __init__(self, scheme_type, pattern):
        """
        Конструктор класса Scheme.

        :param scheme_type: str - тип схемы ("knitting" или "embroidery")
        :param pattern: list[list] - двумерный массив, представляющий схему
        """
        if scheme_type.lower() not in ['knitting', 'embroidery']:
            raise Exception('Invalid scheme type')
        self.scheme_type = scheme_type
        self.pattern = pattern

    def get_pattern(self):
        return self.pattern

    def get_scheme_type(self):
        return self.scheme_type

    def encode(self) -> str:
        """Сжимает схему в форматированную строку."""
        encoded = []
        for row in self.pattern:
            if not row:
                continue

            current_char = row[0]
            count = 1

            for char in row[1:]:
                if char == current_char:
                    count += 1
                else:
                    encoded.append(f"{count}{self._escape_char(current_char)}")
                    current_char = char
                    count = 1

            encoded.append(f"{count}{self._escape_char(current_char)}")
            encoded.append("^")  # Разделитель строк

        return "".join(encoded[:-1])

    def _escape_char(self, char):
        """Экранирует специальные символы."""
        if char in ("\\", "^") or char.isdigit():
            return f"\\{char}"
        return char

    @classmethod
    def decode(cls, encoded_str: str, scheme_type: str) -> 'Scheme':
        """Разжимает форматированную строку в двумерный массив"""
        pattern = []
        current_row = []
        i = 0
        n = len(encoded_str)

        while i < n:
            if encoded_str[i] == "\\":
                if i + 1 >= n:
                    raise ValueError("Incomplete escape sequence")
                current_row.append(encoded_str[i + 1])
                i += 2
            elif encoded_str[i] == "^":
                pattern.append(current_row)
                current_row = []
                i += 1
            elif encoded_str[i].isdigit():
                num_str = ""
                while i < n and encoded_str[i].isdigit():
                    num_str += encoded_str[i]
                    i += 1

                if i >= n:
                    raise ValueError("Unexpected end of string")

                char = encoded_str[i]
                i += 1

                if char == "\\":
                    if i >= n:
                        raise ValueError("Incomplete escape sequence")
                    char = encoded_str[i]
                    i += 1

                current_row.extend([char] * int(num_str))
            else:
                raise ValueError(f"Invalid character at position {i}: '{encoded_str[i]}'")

        if current_row:
            pattern.append(current_row)

        return cls(scheme_type, pattern)


scheme1 = Scheme("knitting", [["a", "a", "b"], ["c", "d", "d"]])
encoded1 = scheme1.encode()
print(f"Encoded 1: {encoded1}")  #"2a1b^1c2d"
decoded1 = Scheme.decode(encoded1, "knitting")
print(f"Decoded 1: {decoded1.get_pattern()}")  #[['a', 'a', 'b'], ['c', 'd', 'd']]

scheme2 = Scheme("embroidery", [["^", "b", "b"], ["\\", "d", "d"]])
encoded2 = scheme2.encode()
print(f"Encoded 2: {encoded2}")  #"1\^2b^1\\2d"
decoded2 = Scheme.decode(encoded2, "embroidery")
print(f"Decoded 2: {decoded2.get_pattern()}")  #[['^', 'b', 'b'], ['\\', 'd', 'd']]

scheme3 = Scheme("knitting", [["1", "2", "2"], ["3", "4", "4"]])
encoded3 = scheme3.encode()
print(f"Encoded 3: {encoded3}")  #"1\11\22^1\32\4"
decoded3 = Scheme.decode(encoded3, "knitting")
print(f"Decoded 3: {decoded3.get_pattern()}")  #[['1', '2', '2'], ['3', '4', '4']]

scheme4 = Scheme("knitting", [["a", "^", "b"], ["\\", "d", "d"]])
encoded4 = scheme4.encode()
print(f"Encoded 4: {encoded4}")  # "1a1\^1b^1\\2d"
decoded4 = Scheme.decode(encoded4, "knitting")
print(f"Decoded 4: {decoded4.get_pattern()}")  #[['a', '^', 'b'], ['\\', 'd', 'd']]

scheme5 = Scheme("aboba", [["a", "^", "b"], ["\\", "d", "d"]])
encoded4 = scheme5.encode()
print(f"Encoded 5: {encoded4}")  # Exception
decoded4 = Scheme.decode(encoded4, "aboba")
print(f"Decoded 5: {decoded4.get_pattern()}")  # Exception
