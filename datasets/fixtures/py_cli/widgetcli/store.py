class WidgetStore:
    def __init__(self):
        self._items = ['alpha', 'beta']

    def list_names(self):
        return list(self._items)

    def add(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError('name must be non-empty')
        if name in self._items:
            return
        self._items.append(name)

    def legacy_dump(self):
        return ','.join(self._items)
