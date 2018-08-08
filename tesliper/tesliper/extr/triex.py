import re
from collections.abc import Sequence


class Triex:
    """Simple class for generating efficient, trie-based regular expressions.
    As for now it is not full-functioning trie data structure. It's purpose
    is to construct efficient regex from passed list of words/phrases."""

    def __init__(self, phrases=None):
        self.trie = {}
        if phrases:
            self.add(phrases)

    def add(self, phrases):
        if isinstance(phrases, Sequence):
            for phrase in phrases:
                self._add_phrase(phrase)
        elif isinstance(phrases, str):
            self._add_phrase(phrases)
        else:
            raise TypeError(
                f"invalid parameter type: {type(phrases)}, should be str, list "
                f"or tuple."
            )

    def _add_phrase(self, phrase):
        trie = self.trie
        for char in phrase:
            trie = trie.setdefault(char, {})
        trie[''] = 1

    @property
    def pattern(self):
        """Convenience function for obtaining regular expression."""
        return self._make_regex()

    @property
    def regex(self):
        return re.compile(self.pattern)

    def _make_regex(self, trie=None):
        """This part is created by rex and comes from:
        https://gist.github.com/fcicq/3394647
        refactor this code later for training and better code or something.

        Escaping characters was removed."""

        data = self.trie if trie is None else trie
        if '' in data and len(data.keys()) == 1:
            return None

        alt = []
        cc = []
        q = 0
        for char in sorted(data.keys()):
            if isinstance(data[char], dict):
                try:
                    recurse = self._make_regex(data[char])
                    alt.append(char + recurse)
                except Exception:
                    cc.append(char)
            else:
                q = 1
        cconly = not len(alt) > 0  # backport from atiking's gist

        if len(cc) > 0:
            if len(cc) == 1:
                alt.append(cc[0])
            else:
                alt.append('[' + ''.join(cc) + ']')

        if len(alt) == 1:
            result = alt[0]
        else:
            result = "(?:" + "|".join(alt) + ")"

        if q:
            if cconly:
                result += "?"
            else:
                result = "(?:%s)?" % result
        return result


if __name__ == '__main__':
    t = Triex('foobar forobo fororo fooham foobaz foo'.split(' '))
    print(t.pattern)
    t = Triex([r'Frequencies\s+--\s+', r'Frc consts\s+--\s+'])
    print(t.pattern)
